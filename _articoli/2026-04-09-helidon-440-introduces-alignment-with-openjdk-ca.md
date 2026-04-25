---
layout: code
title: "Helidon 4.4.0: Allineamento con OpenJDK Cadence e Supporto attraverso Java Verified Portfolio"
sintesi: >
  Oracle ha rilasciato Helidon 4.4.0 che adotta la cadenza di rilascio di OpenJDK, viene incluso nel Java Verified Portfolio e presenta nuove funzionalità come Helidon Declarative e JSON.
date: 2026-04-09 12:00:00
tech: "java"
tags: ["java"]
link: ""
---
 Titolo: Helidon 4.4.0: Alignimento con OpenJDK Cadence e Supporto attraverso Java Verified Portfolio

Helidon, il framework microservices di Oracle, ha presentato la versione 4.4.0 che include l'allineamento alla cadenzarelease OpenJDK, supporto attraverso il nuovo Java Verified Portfolio, nuove capacità principali e supporto per LangChain4j con aiuti agenti.

Con la versione 4.4.0, Helidon si allinea alla cadenza di rilascio della OpenJDK, cambiando dalla classica versioning semantica a una versioning basata sulla release di JDK. A partire dalla versione JDK 27 prevista per settembre 2026, la versione Helidon 4.4.0 oggi si riferirà a Helidon 27 e adotterà il modello "tip e coda" praticato da OpenJDK.

Helidon sarà incluso nel nuovo Java Verified Portfolio (JVP), un set di strumenti, framework e librerie Java validati da Oracle. L'annuncio del JVP è stato fatto durante JavaOne 2026 e include anche il supporto commerciale per JavaFX che ha richiesto un ripristino da parte di Oracle a causa dell'esigenza di visualizzazioni avanzate nelle applicazioni AI-potenziate.

Helidon Declarative, introdotto in Helidon 4.3.0, consente un modello di programmazione a controllo invertito nella versione SE di Helidon. In origine costituita da tre feature principali (HTTP Server Endpoint, Scheduling e Fault Tolerance), Helidon Declarative aggiunge ora nuove funzionalità come Metrics, Tracing, Security, Validation, WebSocket Server, WebSocket Client e WebServer CORS.

Questa rilascio presenta anche il nuovo Helidon JSON, una libreria di elaborazione JSON ottimizzata per thread virtuali e applicazioni Java moderne. Il nuovo modulo Helidon JSON comprende due componenti: hemidon-json-binding per la serializzazione e deserializzazione di oggetti; ed Helidon-json per la parsing e la generazione fondamentale di JSON.

L'integrazione con LangChain4j, introdotta in Helidon 4.2.0, è stata migliorata con supporto agente. Gli sviluppatori possono sfruttare due pattern di esecuzione comuni: workflows e dynamic agents.

L'esempio seguente, presentato nel post [blog](https://linktoblogpost), mostra come dichiarativamente creare un agente:

```java
@Ai.Agent("helidon-mp-expert")
@Ai.ChatModel("openai-cheap-model")
@Ai.Tools(value = ProjectNameGeneratorTool.class)
@Ai.McpClients(value = {"first-mcp-client", "second-mcp-client"})
public interface HelidonMpExpert {
   // ...
}
```

Agli agenti può essere assegnato un valore dichiarativo, registrati come singleton o configurati attraverso Helidon Config.

Inizialmente conosciuto come J4C (Java per Cloud), Helidon è stato presentato alla comunità Java nel settembre 2018. È stato progettato per essere semplice e veloce, e possiede due versioni: Helidon SE e Helidon MP.

Helidon SE, un API funzionale, comprendeva in origine tre componenti principali per creare un microservizio - il web server, la configurazione e la sicurezza - per sviluppare applicazioni basate su microservices. Un server di applicazione non è richiesto. Con la rilascio di Helidon 2.0 nel giugno 2020, una nuova web client e un client di database sono stati aggiunti a Helidon SE insieme ad una nuova interfaccia della riga di comando.

Helidon MP, un API dichiarativo, è una implementazione delle specifiche MicroProfile. La versione 4.4.0 supporta MicroProfile 6.1.

Le versioni 1.0 attraverso 3.0 di Helidon SE sono state costruite su Netty, il framework di rete asincrono e event-driven. L'interfaccia WebServer include supporto per configurazione, routing, gestione degli errori, metriche e endpoint di stato di salute.

In preparazione per la versione 4.0, Helidon ha presentato in anteprima alpha una nuova web server, codificata Níma nel settembre 2022. Níma, un nome greco che significa filo, è basato su JEP 444, i Thread Virtuali. La nuova web server è stata finalizzata con la rilascio di Helidon 4.0 nel ottobre 2023.

Per maggiori dettagli sulla versione 4.4.0, tra cui cambiamenti di rottura e deprecazioni, si veda le [note della versione](https://linketonotevisione).