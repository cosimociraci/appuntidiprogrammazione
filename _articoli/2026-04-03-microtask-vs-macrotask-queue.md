---
layout: post
title: "Microtask vs Macrotask Queue"
date: 2026-04-03 14:44:52
sintesi: >
  Non tutte le callback hanno la stessa priorità. process.nextTick e Promise.then (microtasks) vengono eseguiti immediatamente dopo ogni operazione, prima del ciclo successivo dell'Event Loop. Un abuso di nextTick può causare la 'starvation' dell'I/O, 
tech: "js"
tags: ["js", "node.js internals & libuv"]
pdf_file: "microtask-vs-macrotask-queue.pdf"
---

## Esigenza Reale
Risolvere bug di precedenza in sistemi ad alta frequenza dove i timer sembrano "scattare" in ritardo rispetto alle promesse.

## Analisi Tecnica
Problema: L'applicazione non risponde all'I/O esterno perché saturata da una catena infinita di microtask ricorsivi. Perché: Uso setImmediate per task non urgenti. Ho scelto di differire la logica alla fase di "Check" dell'Event Loop per permettere al ciclo di completare il polling dell'I/O di rete.

## Esempio Implementativo

```js
* Visualizzo l'ordine esatto di esecuzione delle diverse code per renderlo
* concreto. */
 console.log('1. Synchronous code'); process.nextTick(() => console.log('2.
nextTick (microtask queue #1)')); Promise.resolve().then(() => console.log('3.
Promise.then (microtask queue #2)')); setImmediate(() => console.log('4.
setImmediate (Check phase)')); setTimeout(() => console.log('5. setTimeout
(Timers phase)'), 0); console.log('6. More synchronous code');
// Output garantito: 1, 6, 2, 3, 4 o 5 (4 e 5 dipendono dal sistema), ma SEMPRE
// 2 prima di 3
* Il problema: starvation da nextTick ricorsivo. Questo codice blocca l'I/O
* indefinitamente. */
 function starveIo() 
{ process.nextTick(() => 
{ 
// SBAGLIATO: ricorsione infinita nei microtask 
// L'Event Loop non passa mai alla fase Poll: nessuna connessione HTTP viene
// accettata starveIo(); }
); }
 
// starveIo(); 
// Non eseguire: blocca il server 
* La soluzione: uso setImmediate per operazioni ricorsive che devono cedere il
* controllo all'Event Loop. */
 function processLargeArray(array, index = 0) 
{ if (index >= array.length) return; 
// Elaboro un elemento per volta processElement(array[index]); if (index % 100
// === 0)
{ 
// Ogni 100 elementi, cedo il controllo all'Event Loop setImmediate(() =>
// processLargeArray(array, index + 1));
// CORRETTO: l'I/O può girare }
 else 
{ process.nextTick(() => processLargeArray(array, index + 1)); 
// Per blocchi piccoli va bene }
 }
 
* Implemento un task runner che distingue tra microtask urgenti e macrotask
* deferibili: */
 class EventLoopAwareQueue 
{ constructor() 
{ this.urgentQueue = []; 
// Elaborati con nextTick: bloccano l'I/O this.deferredQueue = []; 
// Elaborati con setImmediate: cedono all'I/O }
 scheduleUrgent(fn) 
{ 
// Uso nextTick SOLO per task che devono essere elaborati prima del prossimo I/O
// Es: completamento di operazioni sincrone, cleanup di stato critico
// process.nextTick(fn); }
 scheduleDeferred(fn) 
{ 
// Uso setImmediate per tutto il resto: permette all'Event Loop di respirare 
// Es: aggiornamento di cache, invio di notifiche, operazioni batch
// setImmediate(fn); }
 }
 
* In Express, scelgo correttamente dove schedulare le operazioni post-request:
* */
 app.post('/data', async (req, res) => 
{ const result = await db.save(req.body); res.json(result); 
// Rispondo subito al client 
// Operazioni post-risposta: uso setImmediate per non ritardare la prossima
// richiesta setImmediate(async () =>
{ await cache.invalidate(req.body.id); 
// Non urgente: può aspettare il prossimo ciclo await
// analytics.track('data_saved', req.body.id);
// Idem }
); }
); 
/* Monitoro il delay dell'Event Loop per rilevare starvation in produzione: */
 let lastCheck = Date.now(); setInterval(() => 
{ const now = Date.now(); const delay = now - lastCheck - 100; 
// Il timer dovrebbe scattare ogni 100ms if (delay > 50) 
{ console.warn(`Event Loop delay: +$
{delay}
ms - possibile starvation da microtask`); }
 lastCheck = now; }
, 100);
```
