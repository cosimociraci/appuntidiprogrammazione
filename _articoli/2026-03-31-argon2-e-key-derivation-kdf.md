---
layout: post
title: "Argon2 e Key Derivation (KDF)"
date: 2026-03-31 18:54:44 
sintesi: "Usare MD5 o SHA256 per le password è inutile contro le GPU moderne (Rainbow Tables). Argon2, vincitore della Password Hashing Competition, è progettato per essere "Memory-Hard": i parametri di memoria, tempo e parallelismo costringono l'attaccante a "
tech: js
tags: [js, "security & cryptography"]
pdf_file: "argon2-e-key-derivation-kdf.pdf"
---

## Esigenza Reale
Memorizzare in modo sicuro le credenziali degli utenti in un database, garantendo resilienza contro leak massivi di dati.

## Analisi Tecnica
Problema: Vulnerabilità degli hash delle password ad attacchi brute-force accelerati da hardware specializzato. Perché: Uso un algoritmo Memory-Hard. Ho scelto Argon2id per bilanciare la protezione contro attacchi side-channel e la resistenza al cracking parallelo estremo.

## Esempio Implementativo

```js
/* Scelgo Argon2id: è la variante raccomandata dal RFC 9106 perché combina la protezione di Argon2i (side-channel) con quella di Argon2d (GPU). */ const argon2 = require('argon2'); /* Calibro i parametri in base all'hardware del server. La regola: il costo deve rendere ogni hash ~300ms sul server. Con hardware dedicato (100x più veloce), ogni tentativo costa comunque 3ms -> rendere il brute-force impraticabile. */ const ARGON2_OPTIONS = { type: argon2.argon2id, memoryCost: 2 ** 16, // 64MB: un attaccante con GPU da 8GB può fare solo ~128 hash in parallelo timeCost: 3, // 3 iterazioni: aumenta il tempo senza aumentare la memoria parallelism: 1, // Thread usati: 1 per evitare che un singolo utente esaurisca la CPU saltLength: 32, // Salt casuale da 32 byte: generato automaticamente da argon2 hashLength: 32 // Output da 256 bit }; /* Funzione di hashing con gestione degli errori e logging dei tempi per monitorare la calibrazione: */ async function hashPassword(plainPassword) { const start = Date.now(); const hash = await argon2.hash(plainPassword, ARGON2_OPTIONS); const elapsed = Date.now() - start; // Monitoro il tempo per rilevare se il server è sovraccarico o se devo ricalibrate if (elapsed < 200) console.warn(`Hash troppo veloce (${elapsed}ms): considera di aumentare i parametri`); if (elapsed > 500) console.warn(`Hash lento (${elapsed}ms): considera di ridurre i parametri`); return hash; } /* Verifica con re-hashing automatico se i parametri sono cambiati (upgrading seamless): */ async function verifyPassword(plainPassword, storedHash, userId) { const isValid = await argon2.verify(storedHash, plainPassword); if (isValid && argon2.needsRehash(storedHash, ARGON2_OPTIONS)) { // Il parametri sono stati aggiornati: re-hasho silenziosamente durante il login const newHash = await hashPassword(plainPassword); await userRepository.updatePasswordHash(userId, newHash); console.info(`Password re-hashata per utente ${userId} con nuovi parametri Argon2`); } return isValid; } /* Endpoint Express con protezione completa: rate limiting + Argon2 + timing jitter */ const rateLimit = require('express-rate-limit'); const loginLimiter = rateLimit({ windowMs: 15 * 60 * 1000, // 15 minuti max: 10, // Max 10 tentativi per IP message: { error: 'Troppi tentativi: riprova tra 15 minuti' } }); app.post('/auth/login', loginLimiter, async (req, res) => { const { email, password } = req.body; const user = await userRepository.findByEmail(email); // Se l'utente non esiste, verifico un hash fittizio per evitare user enumeration via timing const hashToVerify = user?.passwordHash ?? '$argon2id$v=19$m=65536,t=3,p=1$placeholder'; const isValid = user ? await verifyPassword(password, hashToVerify, user.id) : (await argon2.verify(hashToVerify, password), false); if (!isValid) { return res.status(401).json({ error: 'Credenziali non valide' }); } const token = generateJwt(user); res.json({ token }); });
```
