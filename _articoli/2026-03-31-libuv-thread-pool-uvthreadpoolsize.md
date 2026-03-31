---
layout: post
title: "Libuv Thread Pool & UV_THREADPOOL_SIZE"
date: 2026-03-31 19:00:23 
sintesi: "Non tutto in Node è single-threaded: operazioni come FS, DNS e Crypto usano un pool di thread interno. Il default è di soli 4 thread. Saturando questo pool (es. con molti fs.readFile simultanei), le performance crollano. Ottimizzare questa variabile "
tech: js
tags: [js, "node.js internals & libuv"]
pdf_file: "libuv-thread-pool-uvthreadpoolsize.pdf"
---

## Esigenza Reale
Scalare un server che effettua pesanti operazioni di cifratura o hashing (bcrypt) senza bloccare le altre richieste.

## Analisi Tecnica
Problema: Latenza elevata in operazioni asincrone non-network a causa della coda di attesa nella thread pool di Libuv. Perché: Espando il pool di thread. Ho scelto di configurare UV_THREADPOOL_SIZE per allinearlo al carico previsto, permettendo l'esecuzione parallela di task bloccanti a livello di sistema operativo.

## Esempio Implementativo

```js
/* UV_THREADPOOL_SIZE deve essere impostato PRIMA che il runtime Node.js venga inizializzato. Il modo più sicuro è impostarlo come variabile d'ambiente prima del lancio del processo, non tramite process.env durante l'esecuzione. */ // Lancio del processo: UV_THREADPOOL_SIZE=16 node server.js /* Per impostarlo programmaticamente, deve essere la primissima cosa nel file entry point: */ process.env.UV_THREADPOOL_SIZE = String(require('os').cpus().length); const crypto = require('crypto'); // Importo DOPO aver impostato la variabile /* Dimostro il bottleneck con il default di 4 thread: 8 hashing bcrypt simultanei. Con pool=4, i secondi 4 aspettano che i primi 4 finiscano. */ function measureParallelHashing(threadPoolSize) { process.env.UV_THREADPOOL_SIZE = String(threadPoolSize); const bcrypt = require('bcrypt'); const start = Date.now(); let completed = 0; const TOTAL = 8; return new Promise(resolve => { for (let i = 0; i < TOTAL; i++) { bcrypt.hash('password123', 12, (err, hash) => { completed++; if (completed === TOTAL) { resolve(Date.now() - start); } }); } }); } /* Con pool=4: ~2x più lento perché i secondi 4 hash aspettano in coda. Con pool=8: tutti e 8 in parallelo, tempo dimezzato. */ /* Identifico quali operazioni usano la thread pool di Libuv per dimensionarla correttamente: */ // fs.readFile, fs.writeFile, fs.stat -> thread pool // crypto.pbkdf2, crypto.randomBytes, crypto.scrypt -> thread pool // bcrypt, argon2 (librerie native) -> thread pool // DNS lookup (dns.lookup, non dns.resolve) -> thread pool // http.get, net.connect -> NON usano la thread pool (gestiti da epoll/kqueue) /* Monitoraggio della saturazione del thread pool in produzione: */ const { monitorEventLoopDelay } = require('perf_hooks'); const histogram = monitorEventLoopDelay({ resolution: 20 }); histogram.enable(); setInterval(() => { const p99DelayMs = histogram.percentile(99) / 1e6; if (p99DelayMs > 100) { console.warn(`Event Loop P99 delay: ${p99DelayMs.toFixed(2)}ms - possibile saturazione thread pool`); } histogram.reset(); }, 5000); /* In un server Express con bcrypt per l'autenticazione, dimensiono il pool in base al carico atteso: */ // Regola empirica: UV_THREADPOOL_SIZE = min(128, cpuCount * 4) // Per un server con 8 core e 50 login/s concorrenti: UV_THREADPOOL_SIZE=32 const optimalPoolSize = Math.min(128, require('os').cpus().length * 4); process.env.UV_THREADPOOL_SIZE = String(optimalPoolSize); console.log(`Thread pool configurato a ${optimalPoolSize} thread per ${require('os').cpus().length} core`);

```
