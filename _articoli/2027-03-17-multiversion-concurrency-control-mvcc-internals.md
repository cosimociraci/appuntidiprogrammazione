---
layout: code
title: "Multiversion Concurrency Control (MVCC) Internals"
date: 2027-03-17 12:00:00
sintesi: >
  MVCC è il cuore di PostgreSQL: permette ai lettori di non bloccare gli scrittori e viceversa. Ogni riga ha dei metadati nascosti (xmin, xmax) che determinano la visibilità per una specifica transazione. Quando si esegue un UPDATE, Postgres non sovras
tech: "sql"
tags: ["sql", "db", "query"]
pdf_file: "multiversion-concurrency-control-mvcc-internals.pdf"
---

## Esigenza Reale
Ottimizzare un database che subisce migliaia di update al secondo, evitando che la tabella diventi enorme e lenta a causa delle versioni "morte" delle righe.

## Analisi Tecnica
**Problema:** Le vecchie versioni delle righe (dead tuples) occupano spazio e rallentano le scansioni degli indici.

**Perché:** Analizzo xmin e xmax. Ho deciso di monitorare queste colonne di sistema per capire quali transazioni "long-running" stanno impedendo la pulizia MVCC.

## Esempio Implementativo

```sql
    /* Guardo i metadati nascosti per capire lo stato di visibilità. xmin indica
        la transazione che ha creato la riga, xmax quella che l'ha cancellata o
        aggiornata. Se xmax è valorizzato e la transazione corrispondente è
        conclusa, la riga è una dead tuple pronta per il Vacuum. */ SELECT xmin,
        xmax, ctid, * FROM my_table WHERE id = 500; /* Misuro il livello di
        bloat corrente per decidere se serve un intervento manuale. */ SELECT
        relname, n_live_tup, n_dead_tup, round(100.0 * n_dead_tup /
        nullif(n_live_tup + n_dead_tup, 0), 2) AS dead_pct, last_vacuum,
        last_autovacuum FROM pg_stat_user_tables WHERE relname = 'my_table'; /*
        Individuo le transazioni long-running che trattengono le vecchie
        versioni delle righe impedendo al Vacuum di avanzare. */ SELECT pid,
        now() - xact_start AS duration, state, query FROM pg_stat_activity WHERE
        xact_start IS NOT NULL AND now() - xact_start > interval '5 minutes'
        ORDER BY duration DESC; /* Verifico lo snapshot più vecchio attivo nel
        sistema: è il limite invalicabile per il Vacuum. */ SELECT backend_xmin,
        state, query FROM pg_stat_activity WHERE backend_xmin IS NOT NULL ORDER
        BY age(backend_xmin) DESC LIMIT 5;
```
