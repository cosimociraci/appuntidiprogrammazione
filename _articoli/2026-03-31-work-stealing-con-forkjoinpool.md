---
layout: post
title: "Work-Stealing con ForkJoinPool"
date: 2026-03-31 16:50:23 
sintesi: "Per calcoli computazionali pesanti (CPU bound), un pool a dimensione fissa può essere inefficiente se alcuni task sono più lunghi di altri. ForkJoinPool implementa l'algoritmo di work-stealing: i thread inattivi "rubano" lavoro dalle code degli altri"
tech: java
tags: ['java', 'concurrency & multithreading']
pdf_file: "work-stealing-con-forkjoinpool.pdf"
---

## Esigenza Reale
Parallelizzare l'elaborazione di un dataset di grandi dimensioni o il calcolo di una complessa serie statistica in memoria.

## Analisi Tecnica
Problema: Distribuzione non uniforme del carico di lavoro tra i core della CPU, con alcuni core al 100% e altri in idle. Perché: Implemento RecursiveTask. Ho scelto questo pattern perché permette di decomporre il problema ricorsivamente, sfruttando al massimo l'hardware multi-core disponibile.

## Esempio Implementativo

```java
/* Implemento RecursiveTask per sommare un array di long in parallelo. La soglia THRESHOLD determina quando smettere di dividere: troppo bassa causa overhead eccessivo di scheduling, troppo alta riduce il parallelismo. */ public class SumTask extends RecursiveTask<Long> { private static final int THRESHOLD = 10_000; private final long[] data; private final int start, end; public SumTask(long[] data, int start, int end) { this.data = data; this.start = start; this.end = end; } @Override protected Long compute() { if (end - start <= THRESHOLD) { // Ho raggiunto la soglia: processo direttamente senza ulteriori fork long sum = 0; for (int i = start; i < end; i++) sum += data[i]; return sum; } int mid = (start + end) / 2; SumTask left = new SumTask(data, start, mid); SumTask right = new SumTask(data, mid, end); left.fork(); // Avvio il subtask sinistro in asincrono su un altro thread long rightResult = right.compute(); // Calcolo il destro nel thread corrente long leftResult = left.join(); // Aspetto il sinistro return leftResult + rightResult; } } /* Utilizzo il ForkJoinPool comune della JVM (parallelismo = numero di core - 1) oppure ne creo uno dedicato per isolare il carico CPU da altri processi: */ ForkJoinPool pool = new ForkJoinPool(Runtime.getRuntime().availableProcessors()); long[] bigArray = generateData(10_000_000); long result = pool.invoke(new SumTask(bigArray, 0, bigArray.length)); pool.shutdown(); /* In Spring Boot, espongo il calcolo parallelo tramite un service. Uso un ForkJoinPool dedicato per non intaccare il pool comune usato dai parallel stream: */ @Service public class StatisticsService { private final ForkJoinPool cpuPool = new ForkJoinPool( Runtime.getRuntime().availableProcessors() ); public long computeSum(long[] data) { try { return cpuPool.submit(new SumTask(data, 0, data.length)).get(); } catch (InterruptedException | ExecutionException e) { Thread.currentThread().interrupt(); throw new ComputationException("Errore nel calcolo parallelo", e); } } } /* Misuro il guadagno di speedup con JMH o con un semplice benchmark: */ long start = System.nanoTime(); long seqResult = Arrays.stream(bigArray).sum(); // Sequenziale long seqTime = System.nanoTime() - start; start = System.nanoTime(); long parResult = pool.invoke(new SumTask(bigArray, 0, bigArray.length)); long parTime = System.nanoTime() - start; System.out.printf("Speedup: %.2fx%n", (double) seqTime / parTime);
```
