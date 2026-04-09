---
layout: post
title: "Diagnostica: OutOfMemory Nativo"
date: 2027-04-12 12:00:00
sintesi: >
  Se la memoria nativa finisce, la JVM crasha senza un java.lang.OutOfMemoryError classico. Monitorare il processo a livello di sistema operativo (RSS - Resident Set Size) è fondamentale. Se l'heap è vuoto ma il processo occupa 32GB di RAM, il colpevol
tech: "java"
tags: ["java", "jni & project panama"]
pdf_file: "diagnostica-outofmemory-nativo.pdf"
---

## Esigenza Reale
Identificare un leak di memoria silente che causa il riavvio dei pod K8s ogni 48 ore nonostante l'heap Java sia stabile.

## Analisi Tecnica
**Problema:** Crash improvvisi dell'applicazione dovuti all'esaurimento della RAM fisica, non rilevati dai normali monitor Java.
**Perché:** Monitoro i contatori nativi della JVM. Ho scelto di abilitare i log di tracciamento delle Arene per verificare che ogni blocco di memoria nativa abbia un corrispondente evento di chiusura.

## Esempio Implementativo

```java
/* FASE 1: confermo che il leak è nativo e non sull'heap confrontando heap e
    RSS. */
@Scheduled(fixedDelay = 30_000) public void detectNativeMemoryLeak() {
    // Heap Java: gestito dal GC, visibile tramite JMX MemoryUsage heapUsage =
        ManagementFactory.getMemoryMXBean().getHeapMemoryUsage()
    ;
    long heapUsedMB = heapUsage.getUsed() / 1_048_576;
    // RSS del processo: include heap + metaspace + native + stack long rssMB =
        getProcessRssMb()
    ;
    long nativeMemoryEstimateMB = rssMB - heapUsedMB - 512;
    // 512MB stima per metaspace+stack log.info("Heap:
    {
    }
    MB, RSS totale: {
    }
    MB, Stima nativa: {
    }
    MB", heapUsedMB, rssMB, nativeMemoryEstimateMB);
    if (nativeMemoryEstimateMB > 2048 && heapUsedMB < heapUsage.getMax() /
        1_048_576 * 0.5) {
        log.error("POSSIBILE LEAK NATIVO: RAM nativa {
        }
        MB con heap al 50%", nativeMemoryEstimateMB);
        alertService.sendCritical("Leak nativo sospetto: " +
            nativeMemoryEstimateMB + "MB");
    }
}
private long getProcessRssMb() {
    try {
        // Leggo il RSS dal filesystem /proc su Linux long pid =
            ProcessHandle.current().pid()
        ;
        Path statusFile = Path.of("/proc/" + pid + "/status");
        List<String> lines = Files.readAllLines(statusFile);
        return lines.stream() .filter(l -> l.startsWith("VmRSS:")) .mapToLong(l
            -> Long.parseLong(l.replaceAll("[^0-9]", "")) / 1024) .findFirst()
            .orElse(-1);
    }
    catch (IOException e) {
        return -1;
    }
}
/* FASE 2: uso NativeMemoryTracking per identificare quale componente alloca di
    più. */
// Avvio la JVM con: java -XX:NativeMemoryTracking=detail -jar app.jar // Poi in
    produzione: // jcmd <PID> VM.native_memory summary scale=MB // jcmd <PID>
    VM.native_memory detail scale=MB // jcmd <PID> VM.native_memory baseline //
    Aspetto 1 ora // jcmd <PID> VM.native_memory summary.diff scale=MB //
    Confronto con baseline /* FASE 3: per leak nelle Arena Panama, abilito il
    tracking degli Arena non chiuse. */ // java
    -Djdk.foreign.trackSegmentAsyncCleanup=true -jar app.jar /* Implemento un
    wrapper per Arena che logga ogni allocazione e rilascio: */ @Component
    public class TrackedArenaFactory
{
    private final AtomicLong openArenas = new AtomicLong(0);
    private final AtomicLong totalAllocatedBytes = new AtomicLong(0);
    public Arena create(String purpose) {
        openArenas.incrementAndGet();
        return new TrackedArena(Arena.ofConfined(), purpose);
    }
    private class TrackedArena implements Arena {
        private final Arena delegate;
        private final String purpose;
        private final long createdAt = System.currentTimeMillis();
        TrackedArena(Arena delegate, String purpose) {
            this.delegate = delegate;
            this.purpose = purpose;
            log.debug("Arena aperta: {
            }
            (totale aperte: {
            }
            )", purpose, openArenas.get());
        }
        @Override public MemorySegment allocate(long byteSize, long
            byteAlignment) {
            totalAllocatedBytes.addAndGet(byteSize);
            return delegate.allocate(byteSize, byteAlignment);
        }
        @Override public void close() {
            long duration = System.currentTimeMillis() - createdAt;
            if (duration > 60_000) {
                log.warn("Arena '{
                }
                ' rimasta aperta per {
                }
                s: possibile leak", purpose, duration/1000);
            }
            openArenas.decrementAndGet();
            delegate.close();
        }
        @Override public MemorySegment.Scope scope() {
            return delegate.scope();
        }
    }
    /* Espongo le metriche delle Arena tramite Actuator: */
    @Bean public MeterBinder arenaMetrics() {
        return registry -> {
            Gauge.builder("panama.arena.open_count", openArenas,
                AtomicLong::get) .description("Numero di Arena Panama
                attualmente aperte").register(registry);
            Gauge.builder("panama.arena.total_allocated_bytes",
                totalAllocatedBytes, AtomicLong::get) .description("Byte totali
                allocati in memoria nativa").register(registry);
        }
        ;
    }
}
/* FASE 4: per identificare il codice che non chiude l'Arena, uso valgrind in
    ambiente di test. */
// valgrind --leak-check=full --track-origins=yes java -jar app.jar // Valgrind
    traccia ogni malloc/free nativo e identifica i leak con lo stack trace C
    corrispondente /* In Spring Boot, il test di regressione che verifica
    assenza di leak nativi: */ @Test @Tag("memory") public void
    verifyNoNativeLeak() throws Exception
{
    long rssBefore = getRssMb();
    // Eseguo l'operazione sospetta 1000 volte for (int i = 0
    ;
    i < 1000;
    i++) {
        serviceUnderTest.processWithNativeMemory(testData);
    }
    System.gc();
    Thread.sleep(500);
    long rssAfter = getRssMb();
    long leakMB = rssAfter - rssBefore;
    log.info("RSS prima: {
    }
    MB, dopo: {
    }
    MB, delta: {
    }
    MB", rssBefore, rssAfter, leakMB);
    assertTrue(leakMB < 10, "Possibile leak nativo: RSS cresciuto di " + leakMB
        + "MB in 1000 iterazioni");
}
```
