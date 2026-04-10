---
layout: post
title: "Transport Layer Matters per Agenti Intelligenti: Il Perché e Come"
sintesi: >
  L'articolo esplora l'importanza del livello di trasporto per gli agenti intelligenti, spiegando come i concetti come WebSocket di OpenAI migliorino la performance e la scalabilità. Viene presentato un esempio pratico del problema di reinvio della storia della conversazione ed evidenziati i vantaggi e disvantaggi dell'approccio.
date: 2026-04-09 12:00:00
tech: "ia"
tags: ["api", "scalabilità", "performance", "chatbot", "websocket"]
link: ""
---
 Titolo: Transport Layer Matters per Agenti Intelligenti: Il Perché e Come
=============================================================

Nell'ambito dell'IT, il ruolo dei livelli di trasporto è sempre stato fondamentale, ma con la crescita dei sistemi intelligenti e della programmazione automatica, la sua rilevanza ha preso un nuovo profilo. Questo articolo esplora le ragioni per cui i livelli di trasporto sono diventati una preoccupazione prima ordine per gli agenti intelli, come il modo in cui le API stateless crescono male con il contesto e i vantaggi della continuità dello stato.

Introduzione
-------------

Con l'avvento di strumenti come Claude Code, OpenAI Codex, Cursor e Cline che fanno parte del flusso di lavoro quotidiano di molte organizzazioni, soprattutto dopo dicembre 2025, la programmazione automatica degli agenti è diventata sempre più comune. Tuttavia, il trasporto di tali sistemi richiede un'attenzione maggiore rispetto al semplice chat. In questo articolo, vogliamo spiegare come il livello di trasporto può influire significativamente sulla performance e la scalabilità degli agenti intelli.

Il problema del volo aereo
---------------------------

Per dimostrare questa affermazione, possiamo prendere un esempio pratico. Durante un viaggio di linea aerea, ho cercato di usare Claude Code sul web per risolvere qualche problema di codifica. Il problema è stato che la connessione internet era tale che il terzo o quarto giro del loop avevano inizio timeout. Ogni giro richiedeva la ri-invio totale della storia della conversazione, che comprendeva l'intera struttura di codice, le modifiche proposte e i risultati dei test, con un payload che raggiungeva decine di chilobyte. In un link di banda limitata, questo payload era una bottiglia di rete.

Questo esempio ci permette di capire come i livelli di trasporto diventino sempre più importanti per l'utilizzo degli agenti intelli: la conversazione tra il modello e l'utente è composta da molti giri consecutivi, in cui il modello legge il codice, propone modifiche, esegue i test, legge l'output di errore, corregge gli errori e iterando fino alla risoluzione del problema. Ogni giro richiede che il modello riceva la storia completa della conversazione finora; con HTTP, ciò significa che la storia della conversazione deve essere re-inviata ogni volta.

WebSocket di OpenAI
---------------------

In febbraio 2026, OpenAI ha introdotto il modo WebSocket per le risposte API, che memorizza la storia della conversazione nella connessione locale del server, evitando così la re-invio della storia della conversazione.

### Come funziona?

Il client invia una richiesta di origine al server, contenente il sistema, la promessa e i tool (il codice per eseguire). Il server esegue la richiesta e restituisce una risposta. In questa fase iniziale, viene memorizzata nella connessione locale del server.

In seguito, il client invia solo la richiesta seguente contenente l'ID della connessione precedente e le nuove modifiche al codice o i test eseguiti. Il server recupera la risposta memorizzata in cache sulla base dell'ID e restituisce la nuova risposta all'utente.

### Vantaggi

Questo approccio permette di ridurre drasticamente il traffico di rete, consentendo una maggiore scalabilità. Inoltre, poiché il server non deve più ricostruire la storia della conversazione per ogni richiesta, la performance è significativamente migliorata.

### Disavanzi

L'unico svantaggio consiste nel fatto che questa tecnologia non è ancora ampiamente supportata; tuttavia, alcune piattaforme come il WebSocket API forniscono un modo per integrare questa funzionalità in un sito web.

Conclusione
------------

Il livello di trasporto è sempre stato importante per la comunicazione fra le parti, ma con l'avvento di nuove tecnologie e dei sistemi intelligenti, questa importanza si è notevolmente amplificata. Ora che abbiamo capito come funziona WebSocket di OpenAI e come possono migliorare le performance degli agenti intelli, ci aspettiamo che questa tecnologia divenga sempre più diffusa.