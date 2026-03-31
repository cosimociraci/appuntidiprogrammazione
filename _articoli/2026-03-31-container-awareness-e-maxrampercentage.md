---
layout: post
title: "Container Awareness e MaxRAMPercentage"
date: 2026-03-31 16:50:23 
sintesi: "Eseguire Java in un container senza parametri specifici è pericoloso: la JVM potrebbe vedere la memoria totale dell'host invece dei limiti del container, portando al crash (OOM Kill). L'uso di -XX:MaxRAMPercentage invece di -Xmx statico rende l'immag"
tech: java
tags: ['java', 'jvm tuning & garbage collection']
pdf_file: "container-awareness-e-maxrampercentage.pdf"
---

## Esigenza Reale
Evitare che i microservizi su Kubernetes vengano terminati dal sistema operativo (OOMKilled) a causa di una visione errata della memoria disponibile.

## Analisi Tecnica
Problema: Disallineamento tra i limiti di memoria del container e i limiti di allocazione dell'heap della JVM. Perché: Uso le percentuali dinamiche. Ho scelto questo approccio per semplificare il deployment: se cambio le risorse del pod K8s, la JVM si ridimensiona da sola senza dover cambiare la stringa di avvio.

## Esempio Implementativo

```java
/* Configuro la JVM per occupare al massimo il 75% della memoria del container, lasciando spazio per: - Off-heap (Metaspace, Direct Memory, Code Cache): ~15% - Stack dei thread: ~5% - Overhead JVM interno: ~5% */ java -XX:+UseContainerSupport \ -XX:MaxRAMPercentage=75.0 \ -XX:MinRAMPercentage=50.0 \ -XX:InitialRAMPercentage=50.0 \ -jar spring-app.jar /* Verifico che la JVM stia leggendo correttamente i limiti del container: */ java -XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0 -XshowSettings:vm -version // Output atteso: // VM settings: // Max. Heap Size (Estimated): 1.50G // (se il container ha 2GB di limit) /* Nel Kubernetes deployment.yaml, definisco i limiti in modo che la JVM possa calcolare correttamente l'heap: */ // resources: // requests: // memory: "1Gi" // cpu: "500m" // limits: // memory: "2Gi" // cpu: "2000m" /* Con MaxRAMPercentage=75 e limit=2Gi, l'heap sarà ~1.5GB. Senza UseContainerSupport, la JVM vedrebbe la RAM totale del nodo K8s (es. 64GB) e imposterebbe un heap enorme, garantendo l'OOMKill. */ /* Aggiungo nel Dockerfile le opzioni JVM come variabile d'ambiente per permettere l'override a runtime senza ricostruire l'immagine: */ // ENV JAVA_OPTS="-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0 -XX:+UseZGC" // ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app/service.jar"] /* In Spring Boot 3.x, configuro anche il pool di thread Tomcat in base alla memoria disponibile per evitare che troppi thread consumino lo stack oltre i limiti: */ @Bean public TomcatProtocolHandlerCustomizer<?> threadPoolCustomizer() { return handler -> { // Calcolo i thread in base alla RAM disponibile: ogni thread usa ~512KB di stack long maxRam = Runtime.getRuntime().maxMemory(); int maxThreads = (int) Math.min(200, maxRam / (512 * 1024 * 50)); handler.setMaxThreads(maxThreads); handler.setMinSpareThreads(maxThreads / 4); log.info("Tomcat configurato con {} thread max (heap: {}MB)", maxThreads, maxRam / 1_048_576); }; } /* Monitoro l'utilizzo effettivo dell'heap in produzione tramite Actuator: */ // GET /actuator/metrics/jvm.memory.used?tag=area:heap // GET /actuator/metrics/jvm.memory.max?tag=area:heap // Se used/max > 85% costantemente, aumento MaxRAMPercentage o il limit del pod
```
