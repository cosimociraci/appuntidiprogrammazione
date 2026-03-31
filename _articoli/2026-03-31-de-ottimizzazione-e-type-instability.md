---
layout: post
title: "De-ottimizzazione e Type Instability"
date: 2026-03-31 16:39:57 
tech: js
tags: ['js', 'v8 engine & runtime performance']
pdf_file: "de-ottimizzazione-e-type-instability.pdf"
---

## Esigenza Reale
Garantire performance costanti in una libreria di utility usata trasversalmente in un ecosistema micro-frontend.

## Analisi Tecnica
Problema: Jitter nelle performance causato dal compilatore JIT che scarta continuamente il codice ottimizzato per instabilità dei tipi. Perché: Isolo i path di esecuzione per tipo. Ho scelto di creare funzioni specifiche per tipi diversi invece di una funzione "overloaded" generica per mantenere il call site monomorfico.

## Esempio Implementativo

```js
/* Dimostro il problema della Deopt con un esempio misurabile. */ // FUNZIONE POLIMORFICA: causa deopt quando riceve tipi diversi function addPolymorphic(a, b) { return a + b; // L'operatore + ha semantica diversa per number vs string } addPolymorphic(1, 2); // TurboFan ottimizza per number + number addPolymorphic('hello', ' world'); // DEOPT: tipo diverso, TurboFan scarta il codice addPolymorphic(1, 2); // Re-ottimizzazione per gestire entrambi i tipi (megamorphic) /* Verifico le Deopt in Node.js con il flag --trace-deopt: */ // node --trace-deopt --allow-natives-syntax app.js // Output: [deoptimize] reason: wrong type at addPolymorphic /* SOLUZIONE 1: funzioni separate e monomorfiche per tipo. */ function addNumbers(a, b) { // Sempre chiamata con number: TurboFan ottimizza una sola volta return a + b; } function concatStrings(a, b) { // Sempre chiamata con string: path separato return a + b; } /* SOLUZIONE 2: TypeScript per intercettare la polimorfizzazione a compile time. Con TypeScript, l'errore è a compile time, non a runtime: */ // function add(a: number, b: number): number { return a + b; } // add(1, 2); // OK // add('hello', ' world'); // Error TS: Argument of type 'string' is not assignable to parameter of type 'number' /* SOLUZIONE 3: guard espliciti che stabilizzano il tipo prima della funzione calda. */ function processValue(value) { // Normalizzo il tipo all'ingresso: la funzione interna rimane monomorfica if (typeof value === 'string') { return processString(value); } if (typeof value === 'number') { return processNumber(value); } throw new TypeError('Tipo non supportato: ' + typeof value); } // Queste funzioni sono sempre chiamate con un solo tipo: TurboFan le ottimizza perfettamente function processNumber(n) { return n * 2 + 1; } function processString(s) { return s.trim().toLowerCase(); } /* Identifico le funzioni con Deopt frequenti tramite profiling V8: */ // node --prof app.js // node --prof-process isolate-*.log > profile.txt // grep -A 5 "DeoptimizeReason" profile.txt /* In un'applicazione real-world con loop stretto su array di oggetti, garantisco la monomorfia pre-filtrando i tipi: */ function sumValues(items) { // Pre-condizione: tutti gli elementi devono essere number // Se items è un array misto, questa funzione andrà in Deopt al primo elemento non-number let total = 0; for (let i = 0; i < items.length; i++) { total += items[i]; // Monomorfico se items è sempre number[] } return total; } // Uso corretto: sumValues(new Float64Array([1.1, 2.2, 3.3])); // Monomorfico garantito sumValues([1, 2, 3]); // Monomorfico se non mescolo tipi /* Monitoro le Deopt in produzione tramite un custom V8 profiler integrato nel server: */ if (process.env.NODE_ENV === 'development') { // Esporto le statistiche di ottimizzazione delle funzioni critiche setInterval(() => { // %GetOptimizationStatus richiede --allow-natives-syntax const status = %GetOptimizationStatus(sumValues); // 1=interpreted, 2=optimized, 3=always_optimized, 4=never_optimized, 6=maybe_deoptimized console.log('sumValues optimization status:', status); }, 5000); }
```
