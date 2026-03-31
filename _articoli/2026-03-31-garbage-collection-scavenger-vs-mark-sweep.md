---
layout: post
title: "Garbage Collection: Scavenger vs Mark-Sweep"
date: 2026-03-31 19:21:36 
sintesi: "V8 divide l'heap in New Space (piccolo e veloce) e Old Space. La maggior parte degli oggetti muore giovane nello Scavenger GC (copia veloce). Se un oggetto sopravvive troppo, finisce nell'Old Space dove il Mark-Sweep è molto più costoso. Per ridurre "
tech: js
tags: [js, "v8 engine & runtime performance"]
pdf_file: "garbage-collection-scavenger-vs-mark-sweep.pdf"
---

## Esigenza Reale
Ridurre la latenza di "tail" (P99) in un'applicazione real-time soggetta a stop del GC.

## Analisi Tecnica
Problema: Latenze imprevedibili causate da cicli di Garbage Collection pesante sull'Old Generation. Perché: Ottimizzo il ciclo di vita degli oggetti. Ho scelto di favorire oggetti a vita brevissima che possono essere puliti dai cicli veloci dello Scavenger, riducendo la promozione alla memoria a lungo termine.

## Esempio Implementativo

```js
/* Avvio Node con flag di diagnostica per osservare i cicli GC in produzione: */
* // node --trace-gc --trace-gc-verbose app.js // Output tipico: //
* [44315:0x...] Scavenge 2.5 / 8.0 ms -> Minor GC: veloce, < 5ms //
* [44315:0x...] Mark-sweep 120.3 / 256.0 ms -> Major GC: lento, > 100ms /*
* PATTERN CHE CAUSA MAJOR GC: closure che intrappolano riferimenti a grandi
* oggetti. */ const globalCache = new Map(); // Vive per sempre nell'Old Space
* function processRequest(req) { const heavyData = loadData(req.id); // Oggetto
* grande globalCache.set(req.id, heavyData); // SBAGLIATO: heavyData promosso
* all'Old Space return heavyData.result; // Il dato è già stato letto: non serve
* tenerlo in cache } /* PATTERN CORRETTO: oggetti a vita brevissima rimangono
* nel New Space. */ function processRequestOptimized(req) { // heavyData nasce e
* muore nello scope della funzione: Scavenger lo raccoglie const heavyData =
* loadData(req.id); const result = heavyData.result; // Estraggo solo il
* necessario // heavyData viene dereferenziato qui: Scavenger lo pulisce al
* prossimo ciclo return result; // Ritorno solo il primitivo/oggetto piccolo }
* /* Per i casi dove la cache è necessaria, uso WeakRef per permettere al GC di
* raccogliere i valori quando la memoria è sotto pressione: */ class
* PressureAwareLruCache { constructor(maxSize) { this.maxSize = maxSize;
* this.cache = new Map(); // key -> WeakRef(value) this.registry = new
* FinalizationRegistry((key) => { // Callback quando il GC raccoglie l'oggetto:
* rimuovo la entry obsoleta if (this.cache.has(key) &&
* !this.cache.get(key).deref()) { this.cache.delete(key); } }); } set(key,
* value) { if (this.cache.size >= this.maxSize) { // Rimuovo la entry più
* vecchia (prima inserita) const firstKey = this.cache.keys().next().value;
* this.cache.delete(firstKey); } const ref = new WeakRef(value);
* this.cache.set(key, ref); this.registry.register(value, key); // Registro per
* la pulizia automatica } get(key) { const ref = this.cache.get(key); if (!ref)
* return undefined; const value = ref.deref(); if (!value) {
* this.cache.delete(key); // Il GC ha raccolto il valore: rimuovo la entry
* return undefined; } return value; } } /* Identifico quali oggetti vengono
* promossi all'Old Space tramite Chrome DevTools o il profiler integrato di
* Node: */ const v8 = require('v8'); // Scatto un heap snapshot prima function
* takeSnapshot(label) { const snapshot =
* v8.writeHeapSnapshot(`/tmp/heap-${label}-${Date.now()}.heapsnapshot`);
* console.log(`Heap snapshot salvato in ${snapshot}`); } // In produzione,
* monitoraggio continuo del GC tramite performanceObserver: const {
* PerformanceObserver } = require('perf_hooks'); const gcObserver = new
* PerformanceObserver((list) => { for (const entry of list.getEntries()) { const
* gcType = entry.detail?.kind === 1 ? 'Minor (Scavenger)' : 'Major (Mark-
* Sweep)'; const duration = entry.duration.toFixed(2); if (entry.duration > 50)
* { // Loggo solo i GC > 50ms: quelli che impattano P99 console.warn(`GC
* ${gcType}: ${duration}ms - possibile promozione eccessiva all'Old Space`); } }
* }); gcObserver.observe({ entryTypes: ['gc'] }); /* In un server Express,
* espongo le metriche GC tramite un endpoint di health per monitoraggio
* Prometheus: */ app.get('/metrics/gc', (req, res) => { const memUsage =
* process.memoryUsage(); res.json({ heapUsed: Math.round(memUsage.heapUsed /
* 1_048_576) + 'MB', heapTotal: Math.round(memUsage.heapTotal / 1_048_576) +
* 'MB', external: Math.round(memUsage.external / 1_048_576) + 'MB', // Memoria
* nativa (Buffer, Typed Arrays) rss: Math.round(memUsage.rss / 1_048_576) + 'MB'
* // RSS totale del processo }); });
```
