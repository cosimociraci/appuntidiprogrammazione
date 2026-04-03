---
layout: post
title: "WebCrypto API vs Node Crypto"
date: 2026-04-03 14:44:54
sintesi: >
  Storicamente, la crittografia nel browser era lenta e insicura. La WebCrypto API espone operazioni hardware-accelerate e isolate. La differenza fondamentale è tra CryptoKey (oggetti non estraibili dalla memoria JS) e i buffer grezzi: usare chiavi 'no
tech: "js"
tags: ["js", "security & cryptography"]
pdf_file: "webcrypto-api-vs-node-crypto.pdf"
---

## Esigenza Reale
Implementare la cifratura end-to-end (E2EE) in una chat web dove il server non deve mai leggere i messaggi in chiaro.

## Analisi Tecnica
Problema: Esposizione di chiavi crittografiche a script malevoli (XSS) che possono leggere la memoria heap di JavaScript. Perché: Uso chiavi non estraibili. Ho scelto la WebCrypto API per garantire che le operazioni di firma e cifratura avvengano senza mai esporre i byte della chiave al codice applicativo.

## Esempio Implementativo

```js
* Genero una coppia di chiavi ECDH non estraibile per il key exchange della
* E2EE. extractable: false è il parametro CRUCIALE: la chiave privata non può
* mai essere letta come buffer dal codice JS, nemmeno dal nostro. Questo la
* protegge da XSS, da extension malevole e da qualsiasi script sulla pagina. */
 async function generateE2EEKeyPair() 
{ const keyPair = await window.crypto.subtle.generateKey( 
{ name: 'ECDH', namedCurve: 'P-256' }
, false, 
// extractable: false -> la chiave privata non può mai uscire dal browser secure
// context ['deriveKey', 'deriveBits'] ); return keyPair;
// 
{ publicKey: CryptoKey, privateKey: CryptoKey }
 }
 
* Esporto solo la chiave PUBBLICA per inviarla al server/interlocutore. La
* privata rimane inaccessibile. */
 async function exportPublicKey(publicKey) 
{ const exported = await window.crypto.subtle.exportKey('spki', publicKey);
return btoa(String.fromCharCode(...new Uint8Array(exported)));
// Base64 per trasmissione }
 
* Derivo una chiave AES condivisa tramite ECDH: questo è il "segreto" della
* E2EE. */
 async function deriveSharedKey(myPrivateKey, theirPublicKeyBytes) 
{ 
// Importo la chiave pubblica dell'interlocutore const theirPublicKey = await
// window.crypto.subtle.importKey( 'spki', theirPublicKeyBytes,
{ name: 'ECDH', namedCurve: 'P-256' }
, false, [] ); 
// Derivo la chiave AES-GCM condivisa: solo io e il mio interlocutore possiamo
// calcolarla return window.crypto.subtle.deriveKey(
{ name: 'ECDH', public: theirPublicKey }
, myPrivateKey, 
{ name: 'AES-GCM', length: 256 }
, false, 
// La chiave derivata è anch'essa non estraibile ['encrypt', 'decrypt'] ); }
 
* Cifro un messaggio con la chiave condivisa: il server riceve solo il
* ciphertext. */
 async function encryptMessage(sharedKey, plaintext) 
{ const iv = window.crypto.getRandomValues(new Uint8Array(12)); 
// IV casuale a 96 bit per AES-GCM const encoder = new TextEncoder(); const
// ciphertext = await window.crypto.subtle.encrypt(
{ name: 'AES-GCM', iv }
, sharedKey, encoder.encode(plaintext) ); return 
{ iv: Array.from(iv), ciphertext: Array.from(new Uint8Array(ciphertext)) }
; }
 async function decryptMessage(sharedKey, 
{ iv, ciphertext }
) 
{ const decoder = new TextDecoder(); const plaintext = await
window.crypto.subtle.decrypt(
{ name: 'AES-GCM', iv: new Uint8Array(iv) }
, sharedKey, new Uint8Array(ciphertext) ); return decoder.decode(plaintext); }
 
* In Node.js lato server (per operazioni di firma di token o certificati), uso
* il modulo crypto nativo che offre le stesse garanzie di isolamento: */
 const 
{ webcrypto }
 = require('crypto'); const 
{ subtle }
 = webcrypto; 
// Stessa API WebCrypto, disponibile da Node 15+ 
// In Node.js posso anche usare il modulo crypto classico per operazioni server-
// side: const crypto = require('crypto'); const
{ privateKey, publicKey }
 = crypto.generateKeyPairSync('ec', 
{ namedCurve: 'P-256', publicKeyEncoding: 
{ type: 'spki', format: 'pem' }
, privateKeyEncoding: 
{ type: 'pkcs8', format: 'pem' }
 }
);
```
