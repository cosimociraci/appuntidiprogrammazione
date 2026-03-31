---
layout: post
title: "Deep Reflection e Moduli (Project Jigsaw)"
date: 2026-03-31 16:39:57 
tech: java
tags: ['java', 'advanced reflection & metaprogr']
pdf_file: "deep-reflection-e-moduli-project-jigsaw.pdf"
---

## Esigenza Reale
Far funzionare librerie di serializzazione legacy all'interno di un'architettura a moduli Java 17+.

## Analisi Tecnica
Problema: Crash dell'applicazione durante l'accesso via reflection a campi privati di classi interne del JDK o di terze parti. Perché: Configuro l'apertura selettiva dei moduli. Ho scelto di dichiarare esplicitamente quali pacchetti devono essere "aperti" alla reflection per mantenere il controllo sulla sicurezza del sistema.

## Esempio Implementativo

```java
/* Definisco il module-info.java con aperture selettive e granulari. Apro solo i pacchetti strettamente necessari e solo ai moduli che li richiedono, evitando aperture globali che annullerebbero i benefici di Jigsaw. */ module com.myapp { // Esporto l'API pubblica: visibile a tutti i moduli che dichiarano la dipendenza exports com.myapp.api; exports com.myapp.model; // Apro il package model a Jackson per la serializzazione/deserializzazione: // Jackson ha bisogno di accedere ai campi privati per costruire gli oggetti opens com.myapp.model to com.fasterxml.jackson.databind; // Apro il package config a Spring per l'iniezione delle dipendenze opens com.myapp.config to spring.core, spring.beans, spring.context; // Apro il package service a Spring AOP per la generazione dei proxy CGLIB/ByteBuddy opens com.myapp.service to spring.aop, net.bytebuddy; // NON apro com.myapp.internal: rimane completamente incapsulato } /* Per le librerie legacy che usano reflection senza essere module-aware, aggiungo --add-opens nella stringa di avvio JVM come soluzione temporanea: */ // java --add-opens java.base/java.lang=ALL-UNNAMED // --add-opens java.base/java.util=ALL-UNNAMED // --add-opens java.base/sun.nio.ch=ALL-UNNAMED // -jar legacy-app.jar /* In Spring Boot 3.x con moduli Java, configuro il pom.xml per passare automaticamente i --add-opens al plugin maven-surefire per i test: */ // <plugin> // <groupId>org.apache.maven.plugins</groupId> // <artifactId>maven-surefire-plugin</artifactId> // <configuration> // <argLine> // --add-opens java.base/java.lang=ALL-UNNAMED // --add-opens java.base/java.util=ALL-UNNAMED // </argLine> // </configuration> // </plugin> /* Individuo automaticamente le violazioni di accesso ai moduli nei log di avvio: */ @EventListener(ApplicationStartedEvent.class) public void checkModuleAccess() { ModuleLayer layer = ModuleLayer.boot(); // Verifico che i moduli critici siano accessibili per evitare sorprese a runtime layer.findModule("com.fasterxml.jackson.databind").ifPresentOrElse( m -> log.info("Jackson module trovato: {}", m.getName()), () -> log.warn("Jackson module non trovato nel ModuleLayer: possibili problemi di serializzazione") ); } /* Strategia di migrazione graduale da classpath a module path: */ // Fase 1: avvio ancora sul classpath (--class-path) per garantire compatibilità // Fase 2: aggiungo module-info.java con aperture ampie (opens com.myapp to ALL-UNNAMED) // Fase 3: restringo progressivamente le aperture modulo per modulo // Fase 4: rimuovo tutti gli --add-opens dalla stringa di avvio /* Verifico a compile time che non ci siano dipendenze da API interne del JDK usando jdeps: */ // jdeps --jdk-internals --multi-release 17 target/myapp.jar // Output: se vedo "JDK internal API" devo sostituire con API pubbliche prima di Java 21
```
