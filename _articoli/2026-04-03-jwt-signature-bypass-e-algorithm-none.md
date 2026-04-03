---
layout: post
title: "JWT Signature Bypass e Algorithm none"
date: 2026-04-03 14:44:55
sintesi: >
  Molte librerie JWT accettano l'algoritmo 'none', permettendo a un utente di modificare il payload e rimuovere la firma. Il server deve forzare esplicitamente l'algoritmo atteso (es. HS256 o RS256) e rifiutare qualsiasi token che non corrisponda, igno
tech: "js"
tags: ["js", "security & cryptography"]
pdf_file: "jwt-signature-bypass-e-algorithm-none.pdf"
---

## Esigenza Reale
Proteggere un'infrastruttura a microservizi da attacchi di escalation dei privilegi tramite manipolazione dei token.

## Analisi Tecnica
Problema: Validazione insicura dei token JWT che si fida dell'algoritmo dichiarato nell'header del pacchetto ricevuto. Perché: Implemento una "Allow-list" di algoritmi. Ho scelto di ignorare l'header alg del client, forzando il runtime di verifica a usare solo il protocollo crittografico predefinito dal sistema.

## Esempio Implementativo

```js
* Dimostro l'attacco "alg:none" per capire cosa stiamo proteggendo. Un
* attaccante prende un token valido, decodifica l'header e il payload (Base64,
* non cifrato), modifica il payload (es. ruolo 'admin') e ricostruisce il token
* con header
{"alg":"none"}
 e firma vuota. */
 function demonstrateAlgNoneAttack(validToken) 
{ const [header, payload, signature] = validToken.split('.'); 
// Decodifico e modifico il payload const decodedPayload =
// JSON.parse(atob(payload)); decodedPayload.role = 'admin';
// Escalation di privilegi decodedPayload.userId = 1; 
// Impersonificazione 
// Costruisco l'header con alg:none const maliciousHeader = btoa(JSON.stringify(
{ alg: 'none', typ: 'JWT' }
)); const maliciousPayload = btoa(JSON.stringify(decodedPayload)); 
// Firma vuota: alcune librerie vulnerabili accettano questo token! return `$
{maliciousHeader}
.$
{maliciousPayload}
.`; }
 
* PROTEZIONE CORRETTA: forzo l'algoritmo e ignoro completamente l'header del
* token. */
 const jwt = require('jsonwebtoken'); 
// Middleware Express per la validazione sicura dei JWT function
// authenticateToken(req, res, next)
{ const authHeader = req.headers['authorization']; const token =
authHeader?.split(' ')[1]; if (!token) return res.status(401).json(
{ error: 'Token mancante' }
); jwt.verify( token, process.env.JWT_PUBLIC_KEY, 
{ algorithms: ['RS256'], 
// Allow-list ESPLICITA: 'none' e 'HS256' vengono rifiutati issuer:
// 'auth.myapp.com',
// Verifico anche issuer audience: 'api.myapp.com', 
// e audience clockTolerance: 30 
// 30 secondi di tolleranza per skew dell'orologio }
, (err, decoded) => 
{ if (err) 
{ 
// Loggo il tentativo ma non espongo dettagli all'attaccante console.warn('JWT
// validation failed:', err.name, 'from IP:', req.ip); return
// res.status(403).json(
{ error: 'Token non valido' }
); }
 req.user = decoded; next(); }
 ); }
 
* Per architetture a microservizi, implemento la validazione JWT in un
* middleware centralizzato con rotazione delle chiavi: */
 class JwtValidator 
{ constructor(jwksUri) 
{ 
// Carico le chiavi pubbliche dal JWKS endpoint (rotazione automatica)
// this.jwksClient = jwks(
{ jwksUri, cache: true, cacheMaxAge: 600_000, 
// 10 minuti rateLimit: true }
); }
 async validate(token) 
{ 
// Decodifico l'header SENZA verificarlo per ottenere il kid (key ID) const
// decoded = jwt.decode(token,
{ complete: true }
); if (!decoded) throw new Error('Token malformato'); 
// Recupero la chiave pubblica corrispondente al kid dichiarato const key =
// await this.jwksClient.getSigningKey(decoded.header.kid); const publicKey =
// key.getPublicKey();
// Verifico con algoritmo forzato: il kid è solo un hint, l'algoritmo è nostro
// return jwt.verify(token, publicKey,
{ algorithms: ['RS256', 'ES256'], 
// Solo algoritmi asimmetrici forti issuer: process.env.JWT_ISSUER, audience:
// process.env.JWT_AUDIENCE }
); }
 }
```
