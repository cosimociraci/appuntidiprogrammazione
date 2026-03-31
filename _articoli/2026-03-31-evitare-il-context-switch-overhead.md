---
layout: post
title: "Evitare il Context Switch Overhead"
date: 2026-03-31 17:04:41 
sintesi: "Passare da Java a Native ha un costo: la JVM deve salvare lo stato dei registri e gestire i safepoint. Chiamate native troppo frequenti a funzioni microscopiche sono controproducenti. La soluzione è "batchare" il lavoro: meglio passare un intero Memo"
tech: java
tags: ['java', 'jni & project panama']
pdf_file: "evitare-il-context-switch-overhead.pdf"
---

## Esigenza Reale
Ottimizzare un convertitore di formati audio che effettua migliaia di micro-trasformazioni al secondo.

## Analisi Tecnica
Problema: Il costo del "salto" tra Java e C è superiore al tempo di esecuzione della funzione nativa stessa. Perché: Riduco le chiamate cross-boundary. Ho scelto di spostare la logica iterativa nel codice C o di usare segmenti di memoria mappati per far sì che il C legga i dati che Java ha preparato in un'unica soluzione.

## Esempio Implementativo

```java
/* Confronto il costo dei due approcci con JMH per renderlo oggettivo. */ @Benchmark public void manySmallCalls(BenchState state) throws Throwable { // SBAGLIATO: chiamo la funzione nativa per ogni campione audio // Ogni chiamata ha un overhead di ~50-100ns per il context switch JVM->nativo for (int i = 0; i < state.audioSamples.length; i++) { state.convertSampleHandle.invokeExact(state.nativeSrc, (long)i); // 1M chiamate = 50-100ms di overhead puro } } @Benchmark public void oneBigCall(BenchState state) throws Throwable { // CORRETTO: passo l'intero buffer e lascio che il C iteri internamente // 1 sola chiamata nativa = overhead trascurabile (~100ns totali) state.convertBufferHandle.invokeExact(state.nativeSrc, state.nativeDst, state.audioSamples.length); } /* Implemento il servizio di conversione audio con approccio batch: */ @Service public class AudioConversionService { // Handle per la funzione C che converte un intero buffer PCM->AAC private final MethodHandle convertBufferHandle; // Handle per la funzione C che applica un filtro equalizzatore a tutto il buffer private final MethodHandle applyEqualizerHandle; public byte[] convertPcmToAac(short[] pcmSamples, AudioFormat format) throws Throwable { try (Arena arena = Arena.ofConfined()) { // Copio l'intero array PCM in memoria nativa in un'unica operazione MemorySegment src = arena.allocateFrom(ValueLayout.JAVA_SHORT, pcmSamples); // Stimo la dimensione massima AAC int maxAacSize = pcmSamples.length * 2; MemorySegment dst = arena.allocate(maxAacSize); // 1 SOLA chiamata cross-boundary: il C itera internamente sui campioni int outputSize = (int) convertBufferHandle.invokeExact( src, dst, pcmSamples.length, format.getSampleRate(), format.getChannels() ); // Applico l'equalizzatore con un'altra singola chiamata batch applyEqualizerHandle.invokeExact(dst, outputSize, format.getEqualizerBands()); return dst.asSlice(0, outputSize).toArray(ValueLayout.JAVA_BYTE); } } } /* Per operazioni dove il C deve notificare il progresso a Java durante l'elaborazione, uso un MemorySegment condiviso come "canale di comunicazione" invece di upcall frequenti: */ @Service public class ProgressTrackingService { public byte[] processWithProgress(byte[] data, ProgressCallback callback) throws Throwable { try (Arena arena = Arena.ofConfined()) { MemorySegment src = arena.allocateFrom(ValueLayout.JAVA_BYTE, data); MemorySegment dst = arena.allocate(data.length); // Buffer di progresso condiviso: il C scrive la percentuale, Java legge MemorySegment progressBuffer = arena.allocate(ValueLayout.JAVA_INT); // Il C scrive periodicamente il progresso nel buffer invece di fare upcall processWithProgressHandle.invokeExact(src, dst, data.length, progressBuffer); // Java legge il progresso senza context switch: accesso diretto alla memoria while ((int) ValueLayout.JAVA_INT.varHandle().get(progressBuffer, 0L) < 100) { int pct = (int) ValueLayout.JAVA_INT.varHandle().get(progressBuffer, 0L); callback.onProgress(pct); Thread.sleep(10); } return dst.toArray(ValueLayout.JAVA_BYTE); } } }
```
