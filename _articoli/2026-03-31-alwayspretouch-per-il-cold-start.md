---
layout: post
title: "AlwaysPreTouch per il Cold Start"
date: 2026-03-31 16:50:23 
sintesi: "Di default, la JVM riserva la memoria all'avvio ma non la occupa realmente (lazy allocation). Questo causa un calo di performance quando l'applicazione inizia a lavorare seriamente. Il parametro -XX:+AlwaysPreTouch forza la JVM a scrivere uno zero in"
tech: java
tags: ['java', 'jvm tuning & garbage collection']
pdf_file: "alwayspretouch-per-il-cold-start.pdf"
---

## Esigenza Reale
Eliminare le micro-latenze iniziali nei nodi di un cluster che vengono accesi durante i picchi di traffico (autoscaling).

## Analisi Tecnica
Problema: Latenze elevate nelle prime transazioni post-avvio a causa del page-faulting dell'OS durante l'espansione dell'heap. Perché: Uso il PreTouch. Ho scelto di pagare un prezzo in fase di boot per garantire che tutta la memoria dichiarata sia fisicamente pronta e "calda" prima che l'applicazione inizi ad accettare traffico.

## Esempio Implementativo

```java
/* Forzo l'allocazione fisica immediata di tutto l'heap dichiarato. Con -Xms = -Xmx e AlwaysPreTouch, la JVM scrive un byte in ogni pagina da 4KB dell'heap durante lo startup, causando il page-fault in modo controllato prima che arrivi traffico reale. */ java -Xms8G -Xmx8G \ -XX:+AlwaysPreTouch \ -XX:+UseZGC \ -jar latency-sensitive-app.jar /* Misuro l'impatto sul tempo di avvio prima e dopo: */ // Senza AlwaysPreTouch: avvio in 3.2s, prima richiesta in 45ms, p99 prime 100 richieste: 320ms // Con AlwaysPreTouch: avvio in 8.1s, prima richiesta in 8ms, p99 prime 100 richieste: 12ms /* In Kubernetes, AlwaysPreTouch interagisce con i readinessProbe: devo assicurarmi che il probe non scatti prima che il PreTouch sia completato, altrimenti K8s riceve traffico su un pod non ancora "caldo". */ // readinessProbe: // httpGet: // path: /actuator/health/readiness // port: 8080 // initialDelaySeconds: 30 // Aspetto che il PreTouch sia completato // periodSeconds: 5 /* In Spring Boot, posso segnalare esplicitamente la readiness solo dopo che l'applicazione è davvero pronta, includendo un warm-up delle cache: */ @Component public class WarmupReadinessIndicator implements ReadinessHealthContributor { private final AtomicBoolean warmedUp = new AtomicBoolean(false); @EventListener(ApplicationReadyEvent.class) public void onApplicationReady() { // Eseguo query di warm-up per portare i dati in cache warmupCriticalCaches(); warmedUp.set(true); } @Override public HealthComponent getHealth(boolean includeDetails) { return warmedUp.get() ? Health.up().build() : Health.down().withDetail("reason", "Warm-up in corso").build(); } private void warmupCriticalCaches() { log.info("Avvio warm-up cache critiche..."); // Pre-carico le configurazioni più accedute configRepository.findAll().forEach(configCache::put); // Pre-carico gli utenti VIP per evitare cache miss nelle prime richieste userRepository.findVipUsers().forEach(userCache::put); log.info("Warm-up completato: {} config, {} utenti VIP in cache", configCache.size(), userCache.size()); } } /* Per ambienti con autoscaling orizzontale, combino AlwaysPreTouch con un lifecycle hook preStop per dare tempo al pod di drenare le connessioni prima dello spegnimento: */ // lifecycle: // preStop: // exec: // command: ["sh", "-c", "sleep 15"] // 15 secondi per drenare le connessioni in corso
```
