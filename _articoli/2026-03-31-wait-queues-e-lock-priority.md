---
layout: post
title: "Wait Queues e Lock Priority"
date: 2026-03-31 19:00:39 
sintesi: "PostgreSQL gestisce i lock tramite una coda FIFO (First-In-First-Out). Se un processo chiede un Access Exclusive Lock (es. per un ALTER TABLE), si mette in coda. Tutti i processi che arrivano dopo, anche se chiedono solo una semplice SELECT, rimarran"
tech: db
tags: [db, "concorrenza e locking approfond"]
pdf_file: "wait-queues-e-lock-priority.pdf"
---

## Esigenza Reale
Evitare che un tentativo di aggiungere una colonna a una tabella "clienti" blocchi tutte le login degli utenti per minuti.

## Analisi Tecnica
Problema: Una richiesta di manutenzione pesante si mette in testa alla coda e blocca tutte le letture successive, svuotando il pool di connessioni. Perché: Imposto lock_timeout. Ho scelto di far fallire il mio script di migrazione se non ottiene il lock entro 2 secondi, per non disturbare gli utenti.

## Esempio Implementativo

```db
/* Configuro la sessione per non attendere all'infinito. Preferisco che la migrazione fallisca e venga ritentata più tardi, piuttosto che creare un ingorgo che svuota il connection pool. */ SET lock_timeout = '2s'; SET statement_timeout = '30s'; /* Eseguo la migrazione con una strategia di retry esplicita. Se non ottengo il lock, aspetto un momento e riprovo, idealmente in una finestra di bassa attività. */ DO $$ DECLARE max_attempts INT := 5; attempt INT := 0; BEGIN LOOP BEGIN SET LOCAL lock_timeout = '2s'; ALTER TABLE users ADD COLUMN last_login_ip INET; EXIT; -- Se arrivo qui, il lock è stato acquisito e l'ALTER è riuscito EXCEPTION WHEN lock_not_available THEN attempt := attempt + 1; IF attempt >= max_attempts THEN RAISE EXCEPTION 'Impossibile acquisire il lock dopo % tentativi', max_attempts; END IF; RAISE NOTICE 'Tentativo % fallito, aspetto 5 secondi...', attempt; PERFORM pg_sleep(5); END; END LOOP; END $$; /* Per le migrazioni critiche in produzione, la tecnica più sicura è usare ADD COLUMN con un DEFAULT non volatile: in Postgres 11+ questa operazione è istantanea e non riscrive l'intera tabella. */
```
