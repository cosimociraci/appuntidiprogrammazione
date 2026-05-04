---
layout: post
title: "Aggiornamenti tecnici del mio stack Spring"
sintesi: >
  Il post descrive i primi release candidate di varie librerie Spring come Boot, Security, Integration, Modulith, AMQP, Kafka e Vault.
date: 2026-05-03 12:00:00
tech: "java"
tags: ["spring", "boot", "security", "integration", "modulith"]
link: "https://www.infoq.com/news/2026/04/spring-news-roundup-apr20-2026/"
---
## Aggiornamenti tecnici del mio stack Spring dopo l'18 Aprile 2026

Ho assistito ad una serie di aggiornamenti interessanti nel mio stack Spring quest'ultima settimana. Ho visto il rilascio dei primi candidati di versione per Boot, Security, Integration, Modulith, AMQP, Kafka e Vault.

## Spring Boot 4.1.0 RC (Primo Release Candidate)

L'ultima versione candidate di Spring Boot porta correzioni dei bug, migliorie della documentazione, aggiornamenti delle dipendenze e nuove caratteristiche come la supporta per il protocollo OpenTelemetry Protocol (OTLP) SDK esportatore environment variables, oltre alla classe `Spring Framework LazyConnectionDataSourceProxy` per un migliore gestione delle transazioni. [Altre informazioni nel dettaglio sulle note di rilascio](URL_NOTE_DI_RILASCIO).

## Spring Security 7.1.0 RC (Primo Release Candidate)

Il primo release candidate di Spring Security include correzioni dei bug, aggiornamenti delle dipendenze e nuove caratteristiche come un metodo `anyOf()` nella classe `AllRequiredFactorsAuthorizationManager`, che concede l'accesso ad una risorsa tramite l'interfaccia `AuthorizationManager`. Inoltre, supporta il filtro servlet `PreFlightRequestFilter` di nuova generazione che gestisce le richieste pre-flight. [Altre informazioni sulle note di rilascio](URL_NOTE_DI_RILASCIO).

## Spring Session 4.1.0 RC (Primo Release Candidate)

Il primo release candidate di Spring Session fornisce migliorie alla documentazione per riflettere la compatibilità con Spring Boot 4.x. [Altre informazioni sulle note di rilascio](URL_NOTE_DI_RILASCIO).

## Spring Integration 7.1.0 RC (Primo Release Candidate)

Il primo release candidate di Spring Integration porta correzioni dei bug, migliorie della documentazione, aggiornamenti delle dipendenze e nuove caratteristiche come una rifinitura della classe `RedisLockRegistry` che utilizza i comandi Compare-and-Set (CAS) e Compare-and-Delete (CAD) di Redis 8.4+ per il rinnovo e la rilascio delle chiavi di blocco. Inoltre, ci sono migliorie alla classe `JmsChannelFactoryBean` che consente ai utenti di impostare un'istanza personalizzata della classe Spring Framework `JmsTemplate`. [Altre informazioni sulle note di rilascio e su questa pagina](URL_NOTE_DI_RILASCIO_E_SUL_WHATS_NEW).

## Spring Modulith 2.1.0 RC (Primo Release Candidate)

Il primo release candidate di Spring Modulith fornisce correzioni dei bug, aggiornamenti delle dipendenze e migliorie come un nuovo annotazione `@ModuleSlicing` che elimina i fallimenti nelle prove di integrazione per più tipi annotati con `@SpringBootApplication`. Inoltre, ci sono migliorie nella gestione delle transazioni in JobRunr attraverso la decorazione dell'interfaccia Java `DataSource`, che viene inserito nell'interfaccia JobRunr `StorageProvider` per garantire che le transazioni Spring siano considerate come previsto durante l'esterternalizzazione degli eventi. [Altre informazioni sulle note di rilascio](URL_NOTE_DI_RILASCIO).

## Spring AMQP 4.1.0 RC (Primo Release Candidate)

Il primo release candidate di Spring AMQP porta correzioni dei bug, aggiornamenti delle dipendenze e nuove caratteristiche come un metodo `setStopListenerOnFatal()` nella classe `ConditionalRejectingErrorHandler`, che ora tratta gli errori fatali come "fatal" per il listener, non del messaggio. Inoltre, ci sono migliorie all'annotazione `@EnableAmqp` che si allinea semanticamente con la sua controparte `@EnableRabbit`. [Altre informazioni sulle note di rilascio](URL_NOTE_DI_RILASCIO).

## Spring per Apache Kafka 4.1.0 RC (Primo Release Candidate)

Il primo release candidate di Spring per Apache Kafka fornisce correzioni dei bug, migliorie della documentazione, aggiornamenti delle dipendenze e nuove caratteristiche come un enum `ContainerProperties.ShareAckMode` che mappa i casi d'uso (implicito mode, explicit mode and manual) a nomi chiari per le consumer condivise; inoltre, supporta l'interfaccia Apache Kafka `AcknowledgementCommitCallback`, che fornisce visibilità sul successo o sui fallimenti degli commit asincroni. [Altre informazioni sulle note di rilascio e su questa pagina](URL_NOTE_DI_RILASCIO_E_SUL_WHATS_NEW).

## Spring LDAP 4.1.0 RC (Primo Release Candidate)

Il primo release candidate di Spring LDAP include una correzione dei bug, aggiornamenti delle dipendenze e due nuove caratteristiche: la rimozione delle restrizioni riguardo alla dipendenza JUnit 4; inoltre, ci sono rifiniture sulla classe `LdapClient` che aggiunge varie metodi singolo, facoltativo, lista e stream per allineare con l'interfaccia Spring Framework `JdbcClient`. [Altre informazioni sulle note di rilascio](URL_NOTE_DI_RILASCIO).

## Spring Vault 4.1.0 RC (Primo Release Candidate)

Il primo release candidate di Spring Vault fornisce correzioni dei bug, aggiornamenti delle dipendenze e una nuova caratteristica che si basa sulla recente rilascio di HashiCorp Vault 2.0. [Altre informazioni sulle note di rilascio](URL_NOTE_DI_RILASCIO).

---

Fonte originale: https://www.infoq.com/news/2026/04/spring-news-roundup-apr20-2026/