---
layout: post
title: "Locality of Reference e L1/L2 Cache"
date: 2026-03-31 18:54:26 
sintesi: "La CPU legge la memoria a blocchi (cache lines da 64 byte). Un array di oggetti in Java è in realtà un array di puntatori a oggetti sparsi nell'heap (scarsa località). Per massimizzare le performance, la soluzione è usare array di primitivi 1D dove i"
tech: java
tags: [java, "memory & performance"]
pdf_file: "locality-of-reference-e-l1l2-cache.pdf"
---

## Esigenza Reale
Ottimizzare un algoritmo di elaborazione segnali dove l'accesso ai dati deve essere il più veloce possibile.

## Analisi Tecnica
Problema: La CPU passa troppo tempo in attesa che i dati vengano caricati dalla memoria principale a causa della frammentazione dell'heap. Perché: Struttura i dati in array contigui. Ho scelto di appiattire le strutture dati complesse in array lineari per "aiutare" l'hardware a prevedere il prossimo dato da elaborare.

## Esempio Implementativo

```java
/* Confronto il layout in memoria dei due approcci per renderlo concreto. */
// APPROCCIO CON SCARSA LOCALITÀ: array di oggetti // In memoria: [ptr->Point1][ptr->Point2]...[ptr->PointN] // Point1, Point2... sono sparsi nell'heap: ogni accesso è un potenziale cache miss class Point { int x, y; } Point[] points = new Point[1_000_000]; // Array di riferimenti, non di dati // APPROCCIO CON ALTA LOCALITÀ: Structure of Arrays (SoA) // In memoria: [x0][x1][x2]...[xN][y0][y1]...[yN] // I dati x sono tutti contigui: la CPU li prefetcha automaticamente int[] xs = new int[1_000_000]; int[] ys = new int[1_000_000]; /* Implemento un motore di elaborazione segnali con layout SoA per massimizzare il prefetching: */ @Component public class SignalProcessor { // Structure of Arrays: ogni campo è un array separato e contiguo in memoria private int[] timestamps; private float[] amplitudes; private float[] frequencies; private int size; public void loadSignal(SignalData data) { this.size = data.getSampleCount(); this.timestamps = data.getTimestampsArray(); // int[] contiguo this.amplitudes = data.getAmplitudesArray(); // float[] contiguo this.frequencies = data.getFrequenciesArray(); // float[] contiguo } /* Questo loop ha alta località: scansiona tre array contigui in parallelo. La CPU prefetcha automaticamente i blocchi successivi di ogni array. */ public float[] computeEnvelope() { float[] envelope = new float[size]; for (int i = 0; i < size; i++) { // Tutti gli accessi sono sequenziali: L1 cache hit quasi garantito envelope[i] = amplitudes[i] * Math.abs(frequencies[i]); } return envelope; } /* Per operazioni su matrici 2D, accedo sempre per riga (row-major) perché Java memorizza gli array per riga: */ public void processMatrix(float[][] matrix, int rows, int cols) { // CORRETTO: accesso per riga = sequenziale in memoria for (int r = 0; r < rows; r++) { for (int c = 0; c < cols; c++) { matrix[r][c] *= 2.0f; // Accesso sequenziale: prefetch automatico } } // SBAGLIATO: accesso per colonna = salti in memoria = cache miss ad ogni accesso // for (int c = 0; c < cols; c++) // for (int r = 0; r < rows; r++) // matrix[r][c] *= 2.0f; // Salta tra righe diverse: ogni accesso è un cache miss } } /* Misuro l'impatto con JMH, abilitando il profiler delle performance hardware: */ @Benchmark @Fork(jvmArgs = {"-XX:+UnlockDiagnosticVMOptions", "-XX:+PrintInlining"}) public float arrayOfObjects(PointState state) { float sum = 0; for (Point p : state.points) sum += p.x + p.y; // Ogni p.x/p.y è un potenziale cache miss return sum; } @Benchmark public float structOfArrays(SoAState state) { float sum = 0; for (int i = 0; i < state.size; i++) sum += state.xs[i] + state.ys[i]; // Sequenziale: prefetch automatico return sum; } // Risultato tipico: structOfArrays è 3-8x più veloce su array di 1M elementi

```
