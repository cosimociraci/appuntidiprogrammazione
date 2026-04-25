---
layout: post
title: "Sfida di un Senior Developer: La settimana tecnica in Java (aprile 2026)"
sintesi: >
  L'articolo descrive gli aggiornamenti più significativi del mondo Java della settimana, includendo la versione 4.0 di TornadoVM e Google ADK for Java 1.0.
date: 2026-04-09 12:00:00
tech: "java"
tags: ["java"]
link: "https://www.infoq.com/news/2026/04/java-news-roundup-mar30-2026"
---
 # Sfida di un Senior Developer: La settimana tecnica in Java (aprile 2026)

Ho trascorso questa settimana seguendo le notizie più importanti del mondo Java, e sono venuto a conoscenza di alcuni aggiornamenti interessanti. Ho scoperto che la versione 4.0 del framework TornadoVM è stata rilasciata ufficialmente, insieme al Google ADK for Java 1.0.

## TornadoVM 4.0

Il team di sviluppo di TornadoVM ha annunciato la versione 4.0 del loro framework di accelerazione GPU. Il rilascio include varie correzioni dei bug, aggiornamenti delle dipendenze e alcune modifiche significative, tra cui un nuovo hardware backend che supporta Apple Silicon e l'API Metal, la possibilità di utilizzare le intrinseche SIMD shuffle e reduction nel backend PTX, e una nuova funzione `withCUDAGraph()` aggiunta alla classe `TornadoExecutionPlan`. A mio avviso, queste modifiche aprono la strada a nuove possibilità di sviluppo per gli utenti che usano TornadoVM.

## Google ADK for Java 1.0

Google ha annunciato l'uscita della versione 1.0 del loro framework open-source Agent Development Kit (ADK) per Java. Il rilascio include varie correzioni dei bug, miglioramenti della documentazione e alcune nuove funzionalità, tra cui l'utilizzo dell'`InMemoryArtifactService` classe nella classe `AgentExecutorProducer`, per permettere la costruzione di istanze dell'`AgentExecutor`, e la capacità di utilizzare simultaneamente le feature `output_schema` e `tools` in modelli che non supportano entrambi al contempo.

## Altri aggiornamenti

Altre notizie importanti della settimana include:
- La versione 7.1.0 di Grails è stata rilasciata come prima release candidate, con bug fixes e modifiche significative come la configurazione del `Groovy invokedynamic` spostato dalla generata `build.gradle` file al Grails Gradle Plugin per centralizzare la configurazione, e il cambiamento dell'`@Service` annotation che ora eredita un datasource automaticamente dal mapping blocco della classe di dominio.
- Google ha rilasciato le versioni 11.0.21, 10.1.54 e 9.0.117 di Apache Tomcat, con modifiche significative come la risoluzione di un problema che aveva impedito il bloccaggio della scrittura delle risposte in NIO e TLS fino alla chiusura della connessione, e miglioramenti dell'errore handling per HTTP/2 e l'intercettore `EncryptInterceptor`.
- Apache Log4j ha rilasciato la versione 2.25.4 di loro framework di gestione dei log, con alcune modifiche significative come la correzione dell'allineamento tra gli attributi documentati e reali nella classe `Rfc5424Layout` dopo essere stato migrato dal metodo factory al pattern builder in versione 2.21.0, la correzione dei problemi di formattazione e sanitizzazione in XML e RFC5424 layouts, e miglioramenti nell'handling degli invalidi caratteri e valori non standard nella `XmlLayout`, `Log4j1XmlLayout` e `MapMessage` classe.
- Gradle ha rilasciato la prima release candidate di Gradle 9.5.0 con varie modifiche significative, tra cui miglioramenti alla diagnosi e al reporting dei problemi delle task di build, che ora includono informazioni sulla provenienza e un logging più chiaro quando il JVM client non è compatibile, e miglioramenti alla creazione della build con una nuova funzione `disallowChanges()` aggiunta all'interfaccia `DomainObjectCollection`, che permette di impedire l'aggiunta o rimozione degli elementi dalla raccolta.

---
Fonte originale: https://www.infoq.com/news/2026/04/java-news-roundup-mar30-2026/