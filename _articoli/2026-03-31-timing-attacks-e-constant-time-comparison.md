---
layout: post
title: "Timing Attacks e Constant-Time Comparison"
date: 2026-03-31 17:07:22 
sintesi: "Un attaccante può indovinare una password o un token misurando quanto tempo impiega il server a rispondere. Il confronto if (a === b) termina non appena trova un carattere diverso (early exit). Il metodo crypto.timingSafeEqual confronta tutti i byte "
tech: js
tags: ['js', 'security & cryptography']
---

## Esigenza Reale
Proteggere gli endpoint di autenticazione o la verifica di API Key da attacchi di analisi temporale.

## Analisi Tecnica
Problema: Leak di informazioni sensibili tramite la variazione del tempo di esecuzione dei confronti tra stringhe. Perché: Uso il confronto in tempo costante. Ho scelto questa funzione nativa per assicurarmi che il tempo di computazione non dipenda dal numero di caratteri corretti inseriti dall'utente.

## Esempio Implementativo

```js
/* Dimostro il problema del timing attack con un confronto naive. Un attaccante può misurare il tempo di risposta con migliaia di richieste: una chiave che inizia con i caratteri corretti risponderà leggermente più lentamente. */ function vulnerableCompare(userInput, secretKey) { // SBAGLIATO: esce al primo carattere diverso -> tempo dipende dal prefisso corretto return userInput === secretKey; } /* Con enough richieste statistiche, un attaccante può ricostruire la chiave carattere per carattere misurando il tempo di risposta medio. */ /* SOLUZIONE: confronto in tempo costante con crypto.timingSafeEqual. */ const crypto = require('crypto'); function safeCompare(userInput, expected) { // Devo garantire che i buffer abbiano la stessa lunghezza: timingSafeEqual richiede uguale dimensione const inputBuffer = Buffer.from(userInput, 'utf8'); const expectedBuffer = Buffer.from(expected, 'utf8'); // Se le lunghezze sono diverse, il token è sicuramente errato. // Tuttavia devo evitare il timing attack anche sul confronto delle lunghezze: // confronto la lunghezza DOPO aver fatto il timingSafeEqual su buffer dello stesso size. const inputHash = crypto.createHmac('sha256', 'comparison-key').update(inputBuffer).digest(); const expectedHash = crypto.createHmac('sha256', 'comparison-key').update(expectedBuffer).digest(); // Confronto gli hash (sempre 32 byte): nessun leak sulla lunghezza originale return crypto.timingSafeEqual(inputHash, expectedHash); } /* Implemento un middleware per la verifica delle API Key con protezione completa: */ function createApiKeyMiddleware(validApiKeys) { return function apiKeyAuth(req, res, next) { const providedKey = req.headers['x-api-key']; if (!providedKey) { // Aggiungo un delay fisso anche in caso di chiave mancante per non distinguere // "chiave mancante" da "chiave errata" tramite timing return setTimeout(() => res.status(401).json({ error: 'Unauthorized' }), 50); } // Verifico contro tutte le chiavi valide: non esco al primo match per evitare timing leak let isValid = false; for (const validKey of validApiKeys) { // Confronto ogni chiave valida: non uso 'break' per mantenere tempo costante if (safeCompare(providedKey, validKey)) { isValid = true; // Non esco dal loop: continuo per tempo costante } } if (!isValid) { return res.status(403).json({ error: 'Forbidden' }); } next(); }; } /* Aggiungo jitter casuale per rendere impossibile la misurazione statistica anche con timingSafeEqual: */ async function authenticateWithJitter(providedKey, expectedKey) { const startTime = process.hrtime.bigint(); const isValid = safeCompare(providedKey, expectedKey); // Aggiungo un delay casuale tra 10ms e 50ms: il jitter oscura qualsiasi variazione residua const jitterMs = 10 + Math.random() * 40; await new Promise(resolve => setTimeout(resolve, jitterMs)); const elapsed = Number(process.hrtime.bigint() - startTime) / 1e6; console.debug(`Auth completata in ${elapsed.toFixed(2)}ms (include jitter)`); return isValid; }
```
