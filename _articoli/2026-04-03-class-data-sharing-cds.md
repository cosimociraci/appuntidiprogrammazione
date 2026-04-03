---
layout: post
title: "Class Data Sharing (CDS)"
date: 2026-04-03 14:44:34
sintesi: >
  Il caricamento delle classi (parsing dei byte, verifica, creazione metadati) è un costo fisso allo startup. AppCDS permette di scattare una 'fotografia' (archivio .jsa) delle classi già caricate e mapparle direttamente in memoria ai successivi avvii.
tech: "java"
tags: ["java", "advanced reflection & metaprogr"]
pdf_file: "class-data-sharing-cds.pdf"
---

## Esigenza Reale
Ridurre drasticamente il tempo di avvio di istanze serverless o pod Kubernetes che devono scalare rapidamente.

## Analisi Tecnica
Problema: Tempo di avvio dei microservizi troppo lungo, ostacolando le architetture a scaling rapido. Perché: Genero un archivio CDS. Ho scelto di pre-processare le classi dell'applicazione per evitare che la JVM debba rifare lo stesso lavoro di analisi a ogni singolo riavvio del container.

## Esempio Implementativo

```java
* Processo in tre fasi per generare e usare l'archivio CDS. Le fasi 1 e 2
* vengono eseguite una volta sola durante la build dell'immagine Docker. */
 
* FASE 1: eseguo l'app una volta per registrare le classi caricate durante lo
* startup. */
 
// java -XX:DumpLoadedClassList=classes.lst \ 
// -Dspring.context.exit=onRefresh \ 
// -jar app.jar 
// Il flag onRefresh fa terminare Spring Boot subito dopo il refresh del
// contesto:
// cattura tutte le classi caricate durante lo startup senza eseguire il
// business logic
/* FASE 2: creo l'archivio condiviso a partire dalla lista delle classi. */
 
// java -Xshare:dump \ 
// -XX:SharedClassListFile=classes.lst \ 
// -XX:SharedArchiveFile=app.jsa \ 
// -cp app.jar:lib
/* \ 
// org.springframework.boot.loader.JarLauncher 
* FASE 3: ogni avvio usa l'archivio pre-compilato. Il parsing e la verifica del
* bytecode vengono saltati per tutte le classi nell'archivio. */
 
// java -Xshare:on \ 
// -XX:SharedArchiveFile=app.jsa \ 
// -jar app.jar 
/* Misuro la riduzione dello startup time prima e dopo: */
 @SpringBootTest public class StartupTimeTest 
{ @Test public void measureStartupTime() throws Exception 
{ long start = System.currentTimeMillis(); ConfigurableApplicationContext ctx =
SpringApplication.run(MyApplication.class); long startupMs =
System.currentTimeMillis() - start; log.info("Startup time:
{}
ms", startupMs); 
// Senza CDS: ~3200ms, Con CDS: ~1600ms (tipicamente -40/-50%)
// assertTrue(startupMs < 2000, "Startup troppo lento: " + startupMs + "ms");
// ctx.close(); }
 }
 
/* Integro la generazione del CDS nel Dockerfile per Spring Boot: */
 
// FROM eclipse-temurin:21-jre AS cds-builder 
// WORKDIR /app 
// COPY target/app.jar . 
// # Fase 1: genera la lista delle classi 
// RUN java -XX:DumpLoadedClassList=classes.lst \ 
// -Dspring.context.exit=onRefresh -jar app.jar || true 
// # Fase 2: genera l'archivio CDS 
// RUN java -Xshare:dump \ 
// -XX:SharedClassListFile=classes.lst \ 
// -XX:SharedArchiveFile=app.jsa \ 
// -jar app.jar || true 
// FROM eclipse-temurin:21-jre 
// WORKDIR /app 
// COPY --from=cds-builder /app/app.jar . 
// COPY --from=cds-builder /app/app.jsa . 
// ENTRYPOINT ["java", "-Xshare:on", "-XX:SharedArchiveFile=app.jsa", "-jar",
// "app.jar"]
* Per Spring Boot 3.3+, uso il supporto nativo CDS integrato che automatizza le
* fasi 1 e 2: */
 
// ./mvnw spring-boot:process-aot 
// java -Dspring.aot.enabled=true -XX:SharedArchiveFile=app.jsa -jar app.jar 
* Verifico che l'archivio sia effettivamente usato controllando il log di avvio:
* */
 
// java -Xshare:on -XX:SharedArchiveFile=app.jsa -Xlog:class+load=info -jar
// app.jar
// Se vedo "source: shared objects file" per le classi Spring, il CDS funziona
// correttamente
```
