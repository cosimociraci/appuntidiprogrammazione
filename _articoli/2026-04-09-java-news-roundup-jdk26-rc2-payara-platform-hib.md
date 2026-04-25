---
layout: post
title: "Java News Roundup: Febbraio 2026"
sintesi: >
  Riassunto delle principali notizie riguardanti JDK 26, Payara Platform, Hibernate, Quarkus, Apache Camel e Jakarta EE 12.
date: 2026-04-09 12:00:00
tech: "java"
tags: ["java"]
link: ""
---
 # Java News Roundup: Febbraio 2026

Ho trascorso questa settimana seguendo le ultime novità riguardanti il mondo Java, e sono molto entusiasta di condividere ciò che ho appreso con voi. In questo articolo, riassumerò le principali notizie riguardo JDK 26, Payara Platform, Hibernate, Quarkus, Apache Camel e Jakarta EE 12.

## JDK 26

Il secondo release candidate di JDK 26 è stato reso disponibile questa settimana, con numerose aggiornamenti da quello precedente (Build 9). Il team di sviluppo ha risolto alcuni problemi e il GA (release generale) è previsto per il 17 marzo 2026. La versione finale include dieci nuove funzionalità, tra cui:

- JEP 500: Prepare to Make Final Mean Final
- JEP 504: Remove the Applet API
- JEP 516: Ahead-of-Time Object Caching with Any GC
- JEP 517: HTTP/3 per l'API del client HTTP
- JEP 522: G1 GC: Improve Throughput by Reducing Synchronization
- JEP 524: PEM Encodings of Cryptographic Objects (Second Preview)
- JEP 525: Structured Concurrency (Sixth Preview)
- JEP 526: Lazy Constants (Second Preview)
- JEP 529: Vector API (Eleventh Incubator)
- JEP 530: Primitive Types in Patterns, instanceof, e switch (Fourth Preview)

Developers sono incoraggiati a segnalare eventuali bug attraverso il database dei bug Java.

## Payara Platform

Payara ha rilasciato l'edizione di febbraio 2026 del suo Payara Platform, che include Community Edition 7.2026.2, Enterprise Edition 6.35.0 e Enterprise Edition 5.84.0. Gli aggiornamenti includono correzioni dei bug e la migrazione di componenti, così come nuove funzionalità, come l'improved system logging con una nuova proprietà per specificare il sistema di log, e HTTP DELETE requests con un non-zero Content-Length header abilitati di default.

## Hibernate

La versione 8.2.2.Final di Hibernate Search è stata rilasciata questa settimana, con alcune aggiornamenti significativi, tra cui: compatibilità con Hibernate ORM 7.2.4.Final, l'uso di Locale.Root per instanziare i logger e una risoluzione del problema in cui un documento viene aggiornato al posto di eliminato durante un delete cascading quando si applica un'istanza della classe OneToOne dell'ORM Hibernate.

## Quarkus

La versione 3.31.4 del framework Quarkus è stata rilasciata, che include alcuni aggiornamenti significativi come il nuovo isEmpty() metodo nella classe DirectoryPathTree per restaurare la meccanica rimossa nel 3.30 release train per il trattamento dei set di origine vuoti e la risoluzione del problema che ha causato un NullPointerException durante la settimana dell'ambiente variabile HTTP_TEST_HOST con Gradle 9.3.1.

## Apache Camel

La versione 4.18.0 di Apache Camel è stata rilasciata questa settimana, che include correzioni dei bug, aggiornamenti delle dipendenze e nuove funzionalità come un nuovo componente di formato dati Open Cybersecurity Schema Framework (OCFS), un modulo MCP aggiunto alla componente Camel JBang e una classe KafkaSecurityConfigurer aggiunta alla componente Camel Kafka per migliorare la configurazione dell'autenticazione Apache Kafka.

## Jakarta EE 12

I sviluppatori di Jakarta hanno rilasciato un aggiornamento su Jakarta EE 12, con i dettagli della terza milestone contenuti nel minuto della chiamata del platform di Jakarta EE dell'ultima settimana. Le specifiche sono previste per aggiornare il loro pom.xml al nuovo Parent EE4J 2.0.0, che contiene la configurazione necessaria per pubblicare i pacchetti prima della loro pubblicazione su Maven Central, in modo simile a quello precedente OSSRH (ritirato l'anno scorso).

Several specifications have reached a milestone 2 release for Jakarta EE 12. These include:

- Jakarta Contexts and Dependency Injection 5.0
- Jakarta Persistence 4.0
- Jakarta Validation 4.0
- Jakarta RESTful Web Services 5.0
- Jakarta Query 1.0
- Jakarta Data 1.1
- Jakarta NoSQL 1.1

---

Sorgente originale: https://www.infoq.com/news/2026/02/java-news-roundup-feb16-2026/