---
layout: post
title: "Deadlock Timeout e Analisi Log"
date: 2026-04-03 14:40:23
sintesi: "Il parametro deadlock_timeout (default 1s) definisce quanto tempo Postgres aspetta prima di lanciare il controllo del grafo dei lock. Abbassare troppo questo valore aumenta il carico sulla CPU, mentre alzarlo rende il sistema pigro nel risolvere i co"
tech: "db"
tags: ["db", "concorrenza e locking approfond"]
pdf_file: "deadlock-timeout-e-analisi-log.pdf"
---

## Esigenza Reale
Regolare il tempo di reazione del DB ai blocchi circolari in un sistema con transazioni molto brevi e frequenti.

## Analisi Tecnica
Problema: Un deadlock non rilevato rapidamente tiene occupate risorse preziose, ma un controllo troppo frequente rallenta il sistema. Perché: Mantengo il valore di default ma attivo il logging esteso dei lock. Ho scelto questa configurazione per avere visibilità totale senza penalizzare le performance.

## Esempio Implementativo

```db
* Nella sessione di debug, posso abbassare temporaneamente il timeout per
* forzare una rilevazione più rapida e osservare il comportamento. */
 SET deadlock_timeout = '500ms'; 
* Abilito il logging dei lock lenti nel file postgresql.conf per intercettare le
* attese sospette prima che degenerino in deadlock. log_lock_waits = on
* deadlock_timeout = '1s' -- soglia oltre la quale viene loggata l'attesa */
 
* Simulo un deadlock per analizzarne l'output nei log: -- Sessione A: BEGIN;
* UPDATE accounts SET balance = balance - 100 WHERE id = 1; -- poi aggiorna id=2
* -- Sessione B (concorrente): BEGIN; UPDATE accounts SET balance = balance +
* 100 WHERE id = 2; -- poi aggiorna id=1 Nel log troverò: ERROR: deadlock
* detected DETAIL: Process 1234 waits for ShareLock on transaction 5678; blocked
* by process 9012. Process 9012 waits for ShareLock on transaction 5678; blocked
* by process 1234. HINT: See server log for query details. */
 
* La causa radice applicativa più comune è l'ordine di aggiornamento
* inconsistente. La soluzione strutturale è sempre aggiornare le righe nello
* stesso ordine, es. sempre per id crescente: UPDATE accounts SET balance =
* balance + delta WHERE id = ANY(ARRAY[1,2] ORDER BY 1);  */
```
