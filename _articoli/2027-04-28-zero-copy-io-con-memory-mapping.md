---
layout: post
title: "Zero-Copy I/O con Memory Mapping"
date: 2027-04-28 12:00:00
sintesi: >
  Leggere un file da 10GB in Java solitamente richiede di copiarlo dal kernel allo user-space. Il FileChannel.map unito a Panama permette il vero Zero-Copy: il file viene mappato direttamente in un MemorySegment e il sistema operativo caricherà le pagi
tech: "java"
tags: ["java", "jni & project panama"]
pdf_file: "zero-copy-io-con-memory-mapping.pdf"
---

## Esigenza Reale
Analizzare log di dimensioni enormi o database su file senza saturare l'heap Java.

## Analisi Tecnica
**Problema:** L'heap si riempie di byte array temporanei durante la lettura di file di grandi dimensioni.
**Perché:** Uso il Memory Mapping (mmap). Ho scelto di mappare il file direttamente nello spazio di indirizzamento del processo per permettere al kernel di gestire il caching in modo trasparente ed efficiente.

## Esempio Implementativo

```java
/* Implemento un analizzatore di log da file multi-GB che non carica mai
    l'intero file in memoria. Il kernel carica le pagine solo quando le
    accediamo e le scarta quando non servono più. */
@Service public class LargeLogAnalyzer {
    public LogStats analyzeLog(Path logFile) throws Exception {
        try (FileChannel channel = FileChannel.open(logFile,
            StandardOpenOption.READ);
        Arena arena = Arena.ofConfined()) {
            long fileSize = channel.size();
            log.info("Analisi file da {
            }
            GB", fileSize / 1_073_741_824.0);
            // Mappo l'intero file in un MemorySegment: questa operazione è
                istantanea // Il kernel non carica nulla finché non accediamo ai
                byte MemorySegment mmappedFile = channel.map(
                FileChannel.MapMode.READ_ONLY, 0, fileSize, arena )
            ;
            // Scansiono il file cercando le righe ERROR senza mai allocare
                String temporanee long errorCount = 0
            ;
            long warningCount = 0;
            long offset = 0;
            while (offset < fileSize) {
                // Trovo la fine della riga corrente long lineEnd =
                    findNewline(mmappedFile, offset, fileSize)
                ;
                // Lavoro direttamente sul segmento: zero copie if
                    (lineContains(mmappedFile, offset, lineEnd, "ERROR"))
                {
                    errorCount++;
                }
                else if (lineContains(mmappedFile, offset, lineEnd, "WARNING"))
                    {
                    warningCount++;
                }
                offset = lineEnd + 1;
            }
            return new LogStats(errorCount, warningCount);
        }
        // Qui: il mapping viene rilasciato istantaneamente
    }
    private long findNewline(MemorySegment segment, long from, long max) {
        for (long i = from;
        i < max;
        i++) {
            if (segment.get(ValueLayout.JAVA_BYTE, i) == ' ') return i;
        }
        return max;
    }
    private boolean lineContains(MemorySegment segment, long start, long end,
        String pattern) {
        // Confronto i byte del pattern direttamente nel segmento senza creare
            String byte[] patternBytes =
            pattern.getBytes(StandardCharsets.UTF_8)
        ;
        outer: for (long i = start;
        i <= end - patternBytes.length;
        i++) {
            for (int j = 0;
            j < patternBytes.length;
            j++) {
                if (segment.get(ValueLayout.JAVA_BYTE, i + j) !=
                    patternBytes[j]) continue outer;
            }
            return true;
        }
        return false;
    }
}
/* Per file che superano Integer.MAX_VALUE bytes, mappa a chunk: */
public void processHugeFile(Path path) throws Exception {
    try (FileChannel channel = FileChannel.open(path, StandardOpenOption.READ))
        {
        long fileSize = channel.size();
        long chunkSize = 512L * 1024 * 1024;
        // 512MB per chunk for (long offset = 0
        ;
        offset < fileSize;
        offset += chunkSize) {
            long size = Math.min(chunkSize, fileSize - offset);
            try (Arena arena = Arena.ofConfined()) {
                MemorySegment chunk = channel.map(FileChannel.MapMode.READ_ONLY,
                    offset, size, arena);
                processChunk(chunk);
            }
            // Il chunk viene unmappato: la RAM viene liberata per il chunk
                successivo
        }
    }
}
/* Confronto il consumo di memoria con e senza mmap: */
@Test public void compareMemoryUsage() throws Exception {
    long heapBefore = Runtime.getRuntime().totalMemory() -
        Runtime.getRuntime().freeMemory();
    // Approccio classico: legge tutto in heap byte[] allBytes =
        Files.readAllBytes(Paths.get("large-file.log"))
    ;
    // 2GB sull'heap! long heapAfterClassic = Runtime.getRuntime().totalMemory()
        - Runtime.getRuntime().freeMemory()
    ;
    log.info("Heap usato approccio classico: {
    }
    MB", (heapAfterClassic - heapBefore) / 1_048_576);
    // Approccio mmap: zero heap try (FileChannel ch =
        FileChannel.open(Paths.get("large-file.log"), StandardOpenOption.READ)
    ;
    Arena arena = Arena.ofConfined()) {
        MemorySegment mapped = ch.map(FileChannel.MapMode.READ_ONLY, 0,
            ch.size(), arena);
        long heapAfterMmap = Runtime.getRuntime().totalMemory() -
            Runtime.getRuntime().freeMemory();
        log.info("Heap usato approccio mmap: {
        }
        MB", (heapAfterMmap - heapBefore) / 1_048_576);
        // ~0MB
    }
}
```
