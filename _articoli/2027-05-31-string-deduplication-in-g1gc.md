---
layout: post
title: "String Deduplication in G1GC"
date: 2027-05-31 12:00:00
sintesi: >
  Le stringhe duplicate sono la causa principale di spreco di memoria in Java. La funzione -XX:+UseStringDeduplication, disponibile per G1GC, analizza l'heap in background e, se trova stringhe identiche, fa sì che puntino allo stesso array di caratteri
tech: "java"
tags: ["java", "jvm tuning & garbage collection"]
pdf_file: "string-deduplication-in-g1gc.pdf"
---

## Esigenza Reale
Ridurre l'impronta di memoria di un gateway che manipola grossi payload JSON con chiavi e valori ripetitivi.

## Analisi Tecnica
**Problema:** L'heap si riempie di istanze diverse di stringhe che hanno lo stesso identico contenuto testuale.
**Perché:** Attivo la deduplicazione automatica. Ho scelto questa via per ottimizzare la memoria in modo trasparente, evitando di gestire manualmente pool di stringhe o logiche di caching complesse nel codice.

## Esempio Implementativo

```java
/* Abilito la deduplicazione e aggiungo il logging per misurare il risparmio
    effettivo. G1 esegue la deduplicazione durante i cicli di Young GC in modo
    incrementale e a bassa priorità. */
java -XX:+UseG1GC \ -XX:+UseStringDeduplication \
    -XX:StringDeduplicationAgeThreshold=3 \
    -Xlog:stringdedup*=debug:file=dedup.log:time \ -Xmx4G \ -jar api-gateway.jar
/* Nel log di deduplicazione cerco il risparmio cumulativo: */
// [stringdedup] Inspected: 1245230 strings // [stringdedup] Skipped: 234120
    (already deduplicated) // [stringdedup] Deduplicated: 892340 strings, saved:
    187MB /* StringDeduplicationAgeThreshold=3 significa che una stringa viene
    considerata per la deduplicazione solo dopo essere sopravvissuta a 3 Young
    GC: evito di deduplicare oggetti temporanei che sarebbero stati raccolti
    comunque. */ /* Identifico le stringhe duplicate più costose nel mio gateway
    JSON con JFR + JDK Mission Control: */ // jcmd <PID> JFR.start name=memory
    settings=profile // jcmd <PID> JFR.dump filename=memory.jfr // In Mission
    Control: Memory > Heap Live Set > filtra per String /* Le chiavi JSON
    ripetute ("userId", "timestamp", "status", "amount") sono i candidati
    perfetti: un gateway che processa 10.000 req/s con payload da 1KB ha queste
    stringhe replicate milioni di volte. */ /* In Spring Boot, posso
    complementare la deduplicazione JVM con un approccio applicativo per le
    stringhe che so essere ripetitive: */ @Component public class
    StringInternPool
{
    // Uso una ConcurrentHashMap come intern pool controllato per le chiavi JSON
        note private final ConcurrentHashMap<String, String> pool = new
        ConcurrentHashMap<>(256)
    ;
    private static final Set<String> KNOWN_KEYS = Set.of( "userId", "timestamp",
        "status", "amount", "currency", "orderId" );
    public String internIfKnown(String s) {
        if (KNOWN_KEYS.contains(s)) {
            return pool.computeIfAbsent(s, k -> k);
        }
        return s;
        // Per le altre stringhe, lascio lavorare la deduplicazione JVM
    }
}
/* Monitoro il risparmio di memoria della deduplicazione tramite JMX: */
@Scheduled(fixedDelay = 60_000) public void logMemoryStats() {
    MemoryMXBean memBean = ManagementFactory.getMemoryMXBean();
    long heapUsed = memBean.getHeapMemoryUsage().getUsed();
    long heapMax = memBean.getHeapMemoryUsage().getMax();
    log.info("Heap: {
    }
    MB / {
    }
    MB ({
    }
    %)", heapUsed / 1_048_576, heapMax / 1_048_576, 100 * heapUsed / heapMax);
}
```
