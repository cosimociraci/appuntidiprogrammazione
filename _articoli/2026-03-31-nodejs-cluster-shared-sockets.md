---
layout: post
title: "Node.js Cluster & Shared Sockets"
date: 2026-03-31 19:21:39 
sintesi: "Node.js non scala sui core per default. Il modulo cluster permette al master di creare worker e condividere con loro i file descriptor dei socket. Questo permette a più processi di ascoltare sulla stessa porta. Il master usa un algoritmo Round-Robin "
tech: js
tags: [js, "node.js internals & libuv"]
pdf_file: "nodejs-cluster-shared-sockets.pdf"
---

## Esigenza Reale
Implementare uno scale-out verticale su una macchina con 32 core per gestire 100k connessioni simultanee.

## Analisi Tecnica
Problema: Sotto-utilizzo delle risorse hardware: un solo core al 100% e gli altri 31 inattivi durante i picchi di traffico. Perché: Uso il clustering nativo. Ho scelto di isolare i processi worker per garantire che il crash di uno non tiri giù l'intera infrastruttura e per parallelizzare il carico.

## Esempio Implementativo

```js
/* Implemento un cluster manager robusto con auto-restart dei worker e graceful
* shutdown. */ const cluster = require('cluster'); const os = require('os');
* const process = require('process'); if (cluster.isPrimary) { const numWorkers
* = os.cpus().length; console.log(`Master PID ${process.pid}: avvio
* ${numWorkers} worker`); // Avvio un worker per ogni core CPU disponibile for
* (let i = 0; i < numWorkers; i++) { spawnWorker(); } // Auto-restart: se un
* worker crasha, ne avvio subito uno nuovo cluster.on('exit', (worker, code,
* signal) => { if (signal) { console.log(`Worker ${worker.process.pid} killato
* dal segnale ${signal}: non riavvio`); } else if (code !== 0) {
* console.error(`Worker ${worker.process.pid} crashato (code=${code}): riavvio
* in 1s`); setTimeout(spawnWorker, 1000); // Attendo 1s per evitare restart loop
* } }); // Graceful shutdown: aspetto che i worker finiscano le richieste in
* corso process.on('SIGTERM', () => { console.log('Master: SIGTERM ricevuto,
* avvio graceful shutdown'); for (const worker of
* Object.values(cluster.workers)) { worker.send('shutdown'); // Segnalo ai
* worker di smettere di accettare nuove connessioni } // Forzo la terminazione
* dopo 30 secondi se i worker non si chiudono setTimeout(() => {
* console.warn('Timeout graceful shutdown: forzo la terminazione');
* process.exit(1); }, 30_000); }); // Comunicazione master-worker: raccolta
* metriche aggregate cluster.on('message', (worker, message) => { if
* (message.type === 'metrics') { console.log(`Worker ${worker.id}:
* ${message.requestsPerSecond} req/s`); } }); function spawnWorker() { const
* worker = cluster.fork(); console.log(`Worker ${worker.process.pid} avviato`);
* return worker; } } else { // CODICE WORKER: ogni worker è un processo Node.js
* indipendente const express = require('express'); const app = express();
* app.get('/health', (req, res) => { res.json({ status: 'ok', pid: process.pid,
* workerId: cluster.worker.id }); }); app.get('/data', async (req, res) => {
* const result = await db.query(req.query); res.json(result); }); // Graceful
* shutdown del worker: smette di accettare nuove connessioni
* process.on('message', (msg) => { if (msg === 'shutdown') { server.close(() =>
* { console.log(`Worker ${process.pid}: shutdown completato`); process.exit(0);
* }); } }); const server = app.listen(8080, () => { console.log(`Worker
* ${process.pid} in ascolto su :8080`); }); // Metriche periodiche al master let
* requestCount = 0; app.use((req, res, next) => { requestCount++; next(); });
* setInterval(() => { process.send({ type: 'metrics', requestsPerSecond:
* requestCount }); requestCount = 0; }, 1000); } /* Per applicazioni
* containerizzate (Docker/K8s), il clustering non è sempre la scelta giusta:
* preferisco più container con un worker ciascuno per avere isolamento, rolling
* deploy e scaling indipendente. Il cluster è ottimale per VM bare-metal o
* quando non si vuole overhead Docker. */
```
