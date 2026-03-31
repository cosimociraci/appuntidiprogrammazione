---
layout: post
title: "Evitare il False Sharing con @Contended"
date: 2026-03-31 16:50:23 
sintesi: "A livello hardware, la CPU carica i dati in cache lines (solitamente 64 byte). Se due variabili diverse usate da thread diversi finiscono nella stessa linea, la modifica di una invalida la cache dell'altro core, facendo crollare le performance. L'ann"
tech: java
tags: ['java', 'concurrency & multithreading']
pdf_file: "evitare-il-false-sharing-con-contended.pdf"
---

## Esigenza Reale
Massimizzare le performance di contatori atomici globali usati intensivamente in un sistema di trading ad alta frequenza.

## Analisi Tecnica
Problema: Degradazione invisibile delle prestazioni dovuta alla contesa della cache line tra core diversi. Perché: Uso @jdk.internal.vm.annotation.Contended. Ho deciso di forzare l'allineamento della memoria per evitare il ping-pong della cache line tra i core, aumentando il throughput delle operazioni atomiche.

## Esempio Implementativo

```java
/* Il problema: due contatori nello stesso oggetto probabilmente finiscono nella stessa cache line da 64 byte. Quando il thread A incrementa successCount e il thread B incrementa errorCount, si invalidano le cache line a vicenda anche se lavorano su dati diversi. */ public class MetricsBad { public volatile long successCount; // Probabilmente nella stessa cache line di errorCount public volatile long errorCount; // False sharing garantito } /* La soluzione: @Contended aggiunge padding prima e dopo la variabile, garantendo che occupi una cache line da sola. */ public class MetricsGood { @jdk.internal.vm.annotation.Contended public volatile long successCount; // Cache line dedicata: 64 byte di padding prima e dopo @jdk.internal.vm.annotation.Contended public volatile long errorCount; // Idem: nessun thread interferisce con l'altro } /* Richiede il flag JVM: -XX:-RestrictContended per funzionare fuori dai moduli JDK interni. In produzione aggiungo il flag nelle opzioni della JVM: java -XX:-RestrictContended -jar myapp.jar */ /* Per evitare la dipendenza da API interne, posso implementare il padding manualmente con campi dummy. Questa tecnica è usata da LongAdder e ConcurrentHashMap internamente: */ public class PaddedCounter { // 7 long di padding prima del valore (7 * 8 = 56 byte) volatile long p1, p2, p3, p4, p5, p6, p7; volatile long value; // Il valore reale occupa la sua cache line volatile long q1, q2, q3, q4, q5, q6, q7; // 7 long di padding dopo } /* In scenari reali preferisco LongAdder di Java che risolve il problema internamente usando un array di celle con padding, ed è anche più performante di AtomicLong sotto alta contesa: */ public class TradingMetrics { // LongAdder usa striping interno con padding: zero false sharing private final LongAdder successCount = new LongAdder(); private final LongAdder errorCount = new LongAdder(); public void recordSuccess() { successCount.increment(); } public void recordError() { errorCount.increment(); } // sum() è eventualmente consistente: perfetto per dashboard di monitoraggio public long getSuccessCount() { return successCount.sum(); } public long getErrorCount() { return errorCount.sum(); } } /* Misuro l'impatto del false sharing con JMH per quantificare il guadagno prima di introdurre complessità: */ @State(Scope.Benchmark) public class FalseSharingBenchmark { MetricsBad bad = new MetricsBad(); MetricsGood good = new MetricsGood(); @Benchmark @Threads(8) public void withFalseSharing() { bad.successCount++; } @Benchmark @Threads(8) public void withoutFalseSharing() { good.successCount++; } }
```
