---
layout: post
title: "Diagnosticare il GC Thrashing"
date: 2026-03-31 19:00:00 
sintesi: "Quando l'heap è quasi pieno, il GC gira continuamente cercando di liberare pochi KB (thrashing). Se il tempo di GC supera il 90% del tempo totale e libera meno del 2% della memoria, l'applicazione è in coma. I flag GCTimeLimit e GCHeapFreeLimit perme"
tech: java
tags: [java, "jvm tuning & garbage collection"]
pdf_file: "diagnosticare-il-gc-thrashing.pdf"
---

## Esigenza Reale
Implementare un sistema di "fail-fast" per istanze di microservizi che sono entrate in uno stato di degrado irreversibile della memoria.

## Analisi Tecnica
Problema: L'applicazione non risponde più ma il processo risulta attivo, consumando il 100% della CPU in cicli di GC inutili. Perché: Uso le soglie di overhead del GC. Ho scelto di forzare un crash controllato per permettere all'orchestratore (K8s) di riavviare l'istanza su un altro nodo, ripristinando il servizio.

## Esempio Implementativo

```java
/* Configuro la JVM per lanciare un OOM se il GC spende più del 95% del tempo senza liberare almeno il 5% dell'heap. Questo trasforma il thrashing silenzioso in un crash esplicito che K8s può gestire. */ java -XX:+UseG1GC \ -XX:GCTimeLimit=95 \ -XX:GCHeapFreeLimit=5 \ -XX:+HeapDumpOnOutOfMemoryError \ -XX:HeapDumpPath=/var/log/heap-dump.hprof \ -XX:OnOutOfMemoryError="kill -9 %p" \ -jar resilient-app.jar /* HeapDumpOnOutOfMemoryError garantisce che al momento del crash venga salvato il dump per analisi post-mortem. OnOutOfMemoryError="kill -9 %p" forza la terminazione immediata del processo: necessario perché alcuni OOM non terminano il processo da soli. */ /* Rilevo il thrashing in anticipo monitorando il GC overhead prima che diventi critico: */ @Scheduled(fixedDelay = 10_000) public void detectGcThrashing() { List<GarbageCollectorMXBean> gcBeans = ManagementFactory.getGarbageCollectorMXBeans(); long totalGcTime = gcBeans.stream().mapToLong(GarbageCollectorMXBean::getCollectionTime).sum(); long totalGcCount = gcBeans.stream().mapToLong(GarbageCollectorMXBean::getCollectionCount).sum(); MemoryUsage heapUsage = ManagementFactory.getMemoryMXBean().getHeapMemoryUsage(); double heapPct = 100.0 * heapUsage.getUsed() / heapUsage.getMax(); // Se l'heap è sopra il 90% e il GC ha fatto più di 10 cicli nell'ultimo intervallo if (heapPct > 90 && totalGcCount > lastGcCount + 10) { log.error("GC THRASHING RILEVATO: heap al {}%, {} cicli GC in 10 secondi", String.format("%.1f", heapPct), totalGcCount - lastGcCount); // Posso scegliere di terminare il processo in modo controllato invece di aspettare l'OOM if (heapPct > 95) { log.error("Heap critico: avvio shutdown controllato per permettere il riavvio da K8s"); SpringApplication.exit(applicationContext, () -> 1); } } lastGcCount = totalGcCount; } /* In K8s, configuro il pod per riavviarsi automaticamente in caso di crash con OOM: */ // restartPolicy: Always // resources: // limits: // memory: "2Gi" // L'OOMKill del kernel avviene se la JVM sfora il limit del container /* Aggiungo anche un liveness probe che fallisce se il GC overhead supera una soglia: */ @Component public class GcLivenessIndicator implements LivenessStateHealthContributor { @Override public HealthComponent getHealth(boolean includeDetails) { double gcOverhead = computeGcOverheadPct(); if (gcOverhead > 50) { return Health.broken() .withDetail("gc_overhead_pct", gcOverhead) .withDetail("reason", "GC overhead eccessivo: possibile thrashing") .build(); } return Health.correct().withDetail("gc_overhead_pct", gcOverhead).build(); } }
```
