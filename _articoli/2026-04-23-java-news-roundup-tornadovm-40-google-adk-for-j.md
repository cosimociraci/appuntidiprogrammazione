---
layout: post
title: "Riassunto delle novità tecnologiche di marzo 2026"
sintesi: >
  Il post offre un'osservazione dettagliata sulle ultime versioni di TornadoVM, Google ADK for Java, Grails, Tomcat, Log4j e Gradle.
date: 2026-04-23 12:00:00
tech: "java"
tags: ["java", "tornadovm", "google adk", "grails", "tomcat", "log4j", "gradle"]
link: "https://www.infoq.com/news/2026/04/java-news-roundup-mar30-2026/"
---
Condivido con il vostro pieno consenso i risultati della mia ricerca e delle mie esperienze sulla base dell'articolo recentemente pubblicato su InfoQ. In questo post ti porterò a conoscere la nuova versione di TornadoVM, Google ADK per Java, Grails, Tomcat, Log4j e Gradle.

## TornadoVM 4.0

L'ultima versione GA di TornadoVM è stata rilasciata il giorno 6 aprile del 2026 con bug fixes, aggiornamenti delle dipendenze ed alcuni cambiamenti notevoli come: un nuovo backend hardware che supporta Apple Silicon e l'API Metal; supporto PTX per le intrinseche SIMD shuffle e reduction nella riga di esecuzione di Tornado; la nuova funzione `withCUDAGraph()` aggiunta alla classe `TornadoExecutionPlan` per catturare le operazioni CUDA del graph. Ulteriori dettagli possono essere trovati nelle note della versione JDK 25 e JDK 21.

## Google ADK for Java 1.0

Google ha pubblicato la prima versione di Android Developer Kit (ADK) per Java, una libreria open source che offre correzioni dei bug, miglioramenti della documentazione e nuove funzionalità tra cui l'uso della classe `InMemoryArtifactService` nella classe `AgentExecutorProducer` per costruire un istanza di `AgentExecutor`, consentendo così di utilizzare contemporaneamente le caratteristiche, `output_schema` e `tools`. Ulteriori dettagli possono essere trovati nelle note della versione e InfoQ terrà a seguire con una storia news più dettagliata.

## Grails 7.1.0

La prima release candidate di Grails è stata pubblicata con correzioni dei bug ed alcune modifiche notevoli come: la configurazione del Groovy `invokedynamic` è stata spostata dal file generato `build.gradle` alla Plugin Gradle di Grails per centralizzare la configurazione; il cambiamento dell'annotation `@Service` che ora eredita un datasource automaticamente dalla cartella mapping della classe di dominio. Ulteriori dettagli possono essere trovati nelle note della versione.

## Tomcat 11.0.21, 10.1.54 e 9.0.117

Sono stati rilasciati delle nuove versioni di Apache Tomcat con caratteristiche importanti come: una risoluzione del problema in cui il codice non bloccante per l'invio dei dati NIO e TLS significava che la risposta poteva non essere completamente scritta fino alla chiusura della connessione; migliori error handling per HTTP/2 e la classe di intercettazione `EncryptInterceptor`. Ulteriori dettagli possono essere trovati nelle note delle versioni 11.0.21, 10.1.54 e 9.0.117.

## Apache Log4j

La versione 2.25.4 di Apache Log4j è stata rilasciata con modifiche importanti come: il restauro dell'allineamento tra gli attributi configurati documentati e reali nella classe `Rfc5424Layout` dopo che questa fu migrata dal metodo factory al pattern builder nella versione 2.21.0; la risoluzione dei problemi di formattazione e sanitizzazione in XML e layout RFC5424; e migliori gestione dei caratteri invalidi e valori non standard nelle classi `XmlLayout`, `Log4j1XmlLayout` e `MapMessage`. Ulteriori dettagli possono essere trovati nelle note della versione.

## Gradle 9.5.0

La prima release candidate di Gradle è stata pubblicata con modifiche importanti come: miglioramenti nei diagnostiche e nel reporting delle fail di task che ora includono informazioni sulle provenienze ed un logging più chiaro quando il JVM client non è compatibile; miglioramenti nella scrittura dell'authoring con la nuova funzione `disallowChanges()` aggiunta all'interfaccia `DomainObjectCollection`, in modo che gli elementi non possono più essere aggiunti o rimossi dalla raccolta. Ulteriori dettagli possono essere trovati nelle note della versione.

---
Fonte originale: https://www.infoq.com/news/2026/04/java-news-roundup-mar30-2026/