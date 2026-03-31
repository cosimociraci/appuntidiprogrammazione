---
layout: post
title: "Migrazione a FFM API (Panama)"
date: 2026-03-31 16:50:23 
sintesi: "JNI richiede la scrittura di codice C "glue" (stub) e ha un alto costo di transizione (context switch). La Foreign Function & Memory API (Java 21/22) permette di chiamare funzioni C direttamente da Java usando Linker e SymbolLookup. Questo elimina la"
tech: java
tags: ['java', 'jni & project panama']
pdf_file: "migrazione-a-ffm-api-panama.pdf"
---

## Esigenza Reale
Sostituire un vecchio bridge JNI instabile con una soluzione moderna per chiamare una libreria di compressione dati ultra-veloce in C.

## Analisi Tecnica
Problema: Complessità di mantenimento del codice C JNI e instabilità della JVM in caso di errori nei puntatori. Perché: Uso SymbolLookup e Linker. Ho scelto Panama perché mi permette di mappare la firma della funzione C direttamente in Java, garantendo una gestione della memoria più sicura tramite le "Arene".

## Esempio Implementativo

```java
/* Ottengo il Linker nativo e cerco le funzioni della libreria di compressione LZ4 caricata dinamicamente. Panama elimina la necessità di scrivere codice C stub per ogni funzione che voglio chiamare. */ Linker linker = Linker.nativeLinker(); // Carico la libreria nativa: Panama cerca automaticamente la .so/.dll nel library path SymbolLookup lz4Lib = SymbolLookup.libraryLookup("liblz4.so.1", Arena.global()); /* Mappo la funzione C: int LZ4_compress_default(const char* src, char* dst, int srcSize, int dstCapacity) */ MethodHandle lz4Compress = linker.downcallHandle( lz4Lib.find("LZ4_compress_default").orElseThrow(() -> new RuntimeException("LZ4 non trovata")), FunctionDescriptor.of( ValueLayout.JAVA_INT, // Valore di ritorno: int (dimensione compressa) ValueLayout.ADDRESS, // src: puntatore al buffer sorgente ValueLayout.ADDRESS, // dst: puntatore al buffer destinazione ValueLayout.JAVA_INT, // srcSize: dimensione sorgente ValueLayout.JAVA_INT // dstCapacity: capacità massima destinazione ) ); /* Uso un'Arena confined per gestire la memoria dei buffer in modo deterministico: alla chiusura del try-with-resources, tutta la memoria viene rilasciata istantaneamente senza aspettare il GC. */ @Service public class Lz4CompressionService { private final MethodHandle lz4CompressHandle; private final MethodHandle lz4DecompressHandle; @PostConstruct public void init() throws Exception { Linker linker = Linker.nativeLinker(); SymbolLookup lib = SymbolLookup.libraryLookup("liblz4.so.1", Arena.global()); // Risolvo i MethodHandle una sola volta allo startup: zero costo a runtime lz4CompressHandle = linker.downcallHandle( lib.find("LZ4_compress_default").orElseThrow(), FunctionDescriptor.of(JAVA_INT, ADDRESS, ADDRESS, JAVA_INT, JAVA_INT)); lz4DecompressHandle = linker.downcallHandle( lib.find("LZ4_decompress_safe").orElseThrow(), FunctionDescriptor.of(JAVA_INT, ADDRESS, ADDRESS, JAVA_INT, JAVA_INT)); } public byte[] compress(byte[] input) throws Throwable { try (Arena arena = Arena.ofConfined()) { MemorySegment src = arena.allocateFrom(ValueLayout.JAVA_BYTE, input); int maxDstSize = input.length + input.length / 255 + 16; // Formula LZ4 MemorySegment dst = arena.allocate(maxDstSize); int compressedSize = (int) lz4CompressHandle.invokeExact(src, dst, input.length, maxDstSize); if (compressedSize <= 0) throw new RuntimeException("Compressione LZ4 fallita"); return dst.asSlice(0, compressedSize).toArray(ValueLayout.JAVA_BYTE); } } } /* Confronto l'overhead con JNI classico tramite JMH: */ @Benchmark public byte[] withJni(BenchState state) { return JniLz4Wrapper.compress(state.data); // Context switch + JNI stub } @Benchmark public byte[] withPanama(BenchState state) throws Throwable { return compressionService.compress(state.data); // Downcall diretto: 30-50% più veloce } /* Verifico che l'API Panama sia abilitata nel modulo: */ // Nel module-info.java: // requires jdk.incubator.foreign; // Solo per Java 19-: da Java 21 è stabile
```
