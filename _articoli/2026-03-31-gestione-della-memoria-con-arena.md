---
layout: post
title: "Gestione della Memoria con Arena"
date: 2026-03-31 17:04:41 
sintesi: "La memoria nativa (off-heap) non è vista dal GC: se non viene liberata correttamente, il server crasha. L'Arena di Panama definisce il ciclo di vita della memoria: quando l'Arena viene chiusa (try-with-resources), tutta la memoria allocata al suo int"
tech: java
tags: ['java', 'jni & project panama']
pdf_file: "gestione-della-memoria-con-arena.pdf"
---

## Esigenza Reale
Allocare grandi buffer per elaborazione grafica off-heap che devono essere liberati non appena l'operazione termina.

## Analisi Tecnica
Problema: Difficoltà nel tracciare la liberazione della memoria off-heap in applicazioni multithreaded. Perché: Uso Arena.ofConfined(). Ho scelto questo modello perché garantisce che la memoria appartenga a un solo thread e venga pulita deterministicamente, evitando dangling pointers.

## Esempio Implementativo

```java
/* Esistono quattro tipi di Arena con semantiche diverse: scelgo in base al ciclo di vita e al threading. */ // Arena.ofConfined() -> accesso da un solo thread, liberazione deterministca (try-with-resources) // Arena.ofShared() -> accesso da più thread, liberazione deterministca (thread-safe) // Arena.ofAuto() -> gestita dal GC come un WeakReference (non deterministica, solo per compatibilità) // Arena.global() -> memoria mai liberata: per risorse globali come handle di librerie /* Caso 1: buffer per un'operazione single-thread con ciclo di vita breve. */ @Service public class ImageFilterService { public byte[] applyFilter(byte[] inputImage, FilterParams params) throws Throwable { try (Arena arena = Arena.ofConfined()) { // Confined: solo questo thread può accedere MemorySegment src = arena.allocateFrom(ValueLayout.JAVA_BYTE, inputImage); int outputSize = inputImage.length; // Dimensione output uguale all'input MemorySegment dst = arena.allocate(outputSize); // Chiamo la funzione C del filtro: lavora sui puntatori senza copiare nativeFilterHandle.invokeExact(src, dst, params.getBrightness(), params.getContrast()); return dst.toArray(ValueLayout.JAVA_BYTE); // Copio solo il risultato finale in Java } // Qui: src e dst vengono liberati istantaneamente. Nessuna pressione sul GC. } } /* Caso 2: buffer condiviso tra thread per elaborazione parallela. */ @Service public class ParallelProcessingService { public void processChunks(byte[] data, int chunkCount) throws Exception { try (Arena sharedArena = Arena.ofShared()) { // Shared: più thread possono accedere MemorySegment sharedBuffer = sharedArena.allocateFrom(ValueLayout.JAVA_BYTE, data); List<CompletableFuture<Void>> futures = new ArrayList<>(); int chunkSize = data.length / chunkCount; for (int i = 0; i < chunkCount; i++) { final long offset = (long) i * chunkSize; futures.add(CompletableFuture.runAsync(() -> { // Ogni thread lavora sulla sua slice del buffer condiviso MemorySegment chunk = sharedBuffer.asSlice(offset, chunkSize); processChunkNative(chunk); // Chiamata nativa sicura: Arena è shared })); } CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join(); } // Qui: sharedBuffer viene liberato dopo che tutti i thread hanno finito } } /* Monitoro i leak di Arena in sviluppo abilitando il tracking: */ // java -Djdk.foreign.trackSegmentAsyncCleanup=true -jar app.jar /* Rilevo le Arena non chiuse tramite un test che verifica il cleanup: */ @Test public void verifyArenaCleanup() throws Exception { long initialNativeMemory = getNativeMemoryUsage(); for (int i = 0; i < 1000; i++) { imageFilterService.applyFilter(testImage, FilterParams.defaults()); } System.gc(); long finalNativeMemory = getNativeMemoryUsage(); long leakBytes = finalNativeMemory - initialNativeMemory; assertTrue(leakBytes < 1024, "Possibile leak di Arena: " + leakBytes + " byte non rilasciati"); }
```
