---
layout: post
title: "Subtransactions e Lock Overflow"
date: 2027-02-10 12:00:00
sintesi: >
  L'uso eccessivo di subtransazioni (spesso create da blocchi EXCEPTION nei loop PL/pgSQL o dai Savepoint) può degradare drasticamente le performance dei lock. PostgreSQL tiene traccia delle transazioni in memoria (nello Shared Buffer). Se una transazi
tech: "sql"
tags: ["db", "concorrenza e locking approfond"]
pdf_file: "subtransactions-e-lock-overflow.pdf"
---

## Esigenza Reale
Risolvere rallentamenti improvvisi del database quando si eseguono script di importazione dati che usano molti blocchi TRY-CATCH.

## Analisi Tecnica
**Problema:** Ogni blocco EXCEPTION crea una subtransazione. Se sono troppe, il meccanismo di caching dei lock fallisce.
**Perché:** Riscrivo la logica per validare i dati prima dell'inserimento invece di "provare e catturare l'errore". Ho scelto la validazione preventiva per mantenere pulito lo stack delle transazioni.

## Esempio Implementativo

```sql
    /* PATTERN DA EVITARE: ogni iterazione crea una subtransazione, e con
        migliaia di righe il subxact cache (64 slot in memoria) va in overflow
        su disco, rallentando l'intero cluster. DO $$ DECLARE r RECORD; BEGIN
        FOR r IN SELECT * FROM staging_table LOOP BEGIN INSERT INTO target_table
        VALUES (r.*); EXCEPTION WHEN unique_violation THEN NULL; -- Questo crea
        una subtransazione per ogni riga! END; END LOOP; END $$; */ /* PATTERN
        CORRETTO: elimino la necessità di subtransazioni usando ON CONFLICT, che
        gestisce il conflitto a livello di singola istruzione SQL senza creare
        sotto-transazioni. */ INSERT INTO target_table SELECT * FROM
        staging_table ON CONFLICT (id) DO NOTHING; /* Per importazioni complesse
        dove ho bisogno di validazione preliminare, uso una tabella di staging
        con controlli preventivi: */ INSERT INTO target_table SELECT s.* FROM
        staging_table s WHERE NOT EXISTS ( SELECT 1 FROM target_table t WHERE
        t.id = s.id ) AND s.amount > 0 AND s.email LIKE '%@%'; /* Monitoro il
        numero di subtransazioni attive per individuare transazioni
        problematiche in esecuzione: */ SELECT pid, xact_start, query, (SELECT
        count(*) FROM pg_locks l WHERE l.pid = a.pid AND l.locktype =
        'relation') AS lock_count FROM pg_stat_activity a WHERE state = 'active'
        ORDER BY xact_start NULLS LAST; /* In Spring Boot, la stessa trappola si
        presenta con @Transactional mal annidato. Ogni metodo con REQUIRES_NEW
        crea una subtransazione JDBC: preferisco raccogliere gli errori in una
        lista e gestirli fuori dal loop transazionale. */
```
