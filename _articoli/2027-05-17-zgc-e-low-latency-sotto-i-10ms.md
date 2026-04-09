---
layout: post
title: "ZGC e Low Latency sotto i 10ms"
date: 2027-05-17 12:00:00
sintesi: >
  Con heap molto grandi (>100GB), i classici GC come G1 possono avere pause "Stop-The-World" percepibili. ZGC esegue quasi tutto il lavoro in concorrenza con i thread dell'applicazione. Il vantaggio tecnico è che i tempi di pausa sono costanti e non di
tech: "java"
tags: ["java", "jvm tuning & garbage collection"]
pdf_file: "zgc-e-low-latency-sotto-i-10ms.pdf"
---

## Esigenza Reale
Garantire tempi di risposta costanti per un motore di ricerca interno che gestisce un indice in memoria da 200GB.

## Analisi Tecnica
**Problema:** Picchi di latenza imprevedibili causati dalle pause di garbage collection su heap di grandi dimensioni.
**Perché:** Scelgo ZGC. Ho deciso di dare priorità alla latenza minima rispetto al throughput massimo, configurando la JVM per sfruttare il parallelismo estremo nella marcatura degli oggetti.

## Esempio Implementativo

```java
/* Abilito ZGC con logging dettagliato per monitorare che le pause restino
    effettivamente sotto la soglia desiderata. ZGC usa "colored pointers" per
    tracciare lo stato degli oggetti senza Stop-The-World completi. */
java -XX:+UseZGC \ -Xmx200G \ -XX:ConcGCThreads=12 \
    -Xlog:gc*:file=gc.log:time,level,tags \ -jar search-engine.jar
/* Verifico in tempo reale che le pause siano sotto 10ms leggendo il log: */
// [2026-03-25T10:15:03.123] GC(42) Pause Mark Start 1.234ms //
    [2026-03-25T10:15:03.456] GC(42) Pause Mark End 0.891ms //
    [2026-03-25T10:15:03.789] GC(42) Pause Relocate Start 0.543ms // Le tre
    pause sono indipendenti dalla dimensione dell'heap: sempre < 5ms su
    qualsiasi heap /* Misuro la latenza p99 prima e dopo il passaggio a ZGC con
    un benchmark JMH: */ @BenchmarkMode(Mode.AverageTime)
    @OutputTimeUnit(TimeUnit.MILLISECONDS) @Warmup(iterations = 5)
    @Measurement(iterations = 20) public class LatencyBenchmark
{
    @Benchmark public SearchResult searchWithGCPressure(SearchState state) {
        // Alloco deliberatamente oggetti per simulare pressione GC byte[]
            pressure = new byte[1024]
        ;
        return state.index.search("query");
    }
}
/* In Spring Boot, configuro ZGC nel Dockerfile per garantire la portabilità
    della configurazione: */
// ENTRYPOINT ["java", // "-XX:+UseZGC", // "-Xmx200G", //
    "-XX:ConcGCThreads=12", // "-XX:SoftMaxHeapSize=180G", // Suggerisce a ZGC
    di mantenere l'heap sotto 180GB se possibile //
    "-Xlog:gc*:file=/var/log/gc.log:time,level,tags", // "-jar",
    "/app/search-engine.jar"] /* SoftMaxHeapSize è fondamentale: dice a ZGC di
    cercare di mantenere l'heap più piccolo del massimo, riducendo ulteriormente
    la latenza nelle fasi di relocation. */ /* Monitoro le pause GC in
    produzione tramite Micrometer e le espongo come metrica: */ @Bean public
    MeterBinder zgcPauseMetrics()
{
    return registry -> {
        // Registro un listener sulle notifiche JMX del GC per catturare ogni
            pausa for (GarbageCollectorMXBean gc :
            ManagementFactory.getGarbageCollectorMXBeans())
        {
            if (gc instanceof NotificationEmitter emitter) {
                emitter.addNotificationListener((notif, handback) -> {
                    GarbageCollectionNotificationInfo info =
                        GarbageCollectionNotificationInfo .from((CompositeData)
                        notif.getUserData());
                    double pauseMs = info.getGcInfo().getDuration();
                    Timer.builder("jvm.gc.pause.zgc") .tag("cause",
                        info.getGcCause()) .register(registry)
                        .record(Duration.ofMillis((long) pauseMs));
                }
                , null, null);
            }
        }
    }
    ;
}
```
