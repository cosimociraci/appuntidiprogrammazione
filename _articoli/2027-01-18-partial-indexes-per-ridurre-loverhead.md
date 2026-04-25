---
layout: code
title: "Partial Indexes per ridurre loverhead"
date: 2027-01-18 12:00:00
sintesi: >
  Un errore comune è indicizzare l'intera tabella quando le query filtrano sempre per una condizione specifica (es. solo i record "attivi"). I Partial Indexes includono solo le righe che soddisfano un predicato WHERE. Questo li rende minuscoli, velocis
tech: "sql"
tags: ["sql", "db"]
pdf_file: "partial-indexes-per-ridurre-loverhead.pdf"
---

## Esigenza Reale
Ottimizzare la ricerca di ordini "da processare" in una tabella che contiene milioni di ordini già conclusi.

## Analisi Tecnica
**Problema:** L'indice sulla colonna 'status' è enorme e poco selettivo perché la stragrande maggioranza dei record è nello stato 'COMPLETED'.

**Perché:** Uso un indice parziale. Ho deciso di indicizzare solo le righe dove status != 'COMPLETED', riducendo la dimensione dell'indice del 95% e rendendo i lookup istantanei.

## Esempio Implementativo

```sql
    /* Creo l'indice solo sui dati "caldi". Postgres lo userà automaticamente
        quando la WHERE della query implica la stessa condizione del predicato
        parziale. */ CREATE INDEX idx_orders_pending ON orders (created_at)
        WHERE status = 'PENDING'; /* Verifico che il Planner stia usando
        l'indice parziale e non un Seq Scan: */ EXPLAIN (ANALYZE, BUFFERS)
        SELECT id, customer_id, created_at FROM orders WHERE status = 'PENDING'
        ORDER BY created_at; /* Confronto la dimensione dell'indice parziale con
        quella che avrebbe un indice completo: */ SELECT
        pg_size_pretty(pg_relation_size('idx_orders_pending')) AS
        partial_index_size; -- Es: 128 kB vs potenziali 800 MB per un indice
        completo su milioni di righe /* Estendo il concetto a una coda di job:
        indicizzo solo i task non ancora eseguiti. Quando un task viene
        completato (status -> 'DONE'), esce automaticamente dall'indice,
        mantenendolo piccolo nel tempo. */ CREATE INDEX idx_jobs_queue ON
        background_jobs (priority DESC, scheduled_at ASC) WHERE status IN
        ('QUEUED', 'RETRY'); /* Questa query sul job worker userà l'indice
        parziale e restituirà subito il prossimo task da eseguire: */ SELECT id,
        payload FROM background_jobs WHERE status IN ('QUEUED', 'RETRY') ORDER
        BY priority DESC, scheduled_at ASC FOR UPDATE SKIP LOCKED LIMIT 1; /*
        Creo un indice parziale per i soli utenti non verificati, che sono una
        minoranza ma vengono interrogati frequentemente dal sistema di
        sollecito: */ CREATE INDEX idx_users_unverified ON users (created_at)
        WHERE email_verified = false; /* Monitoro la frequenza d'uso dell'indice
        parziale per confermare che venga effettivamente scelto dal Planner: */
        SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch FROM
        pg_stat_user_indexes WHERE relname = 'orders' AND indexrelname =
        'idx_orders_pending'; /* In Spring Boot con Spring Data JPA, la query
        che sfrutta l'indice parziale deve includere esplicitamente la
        condizione dello stesso predicato, altrimenti il Planner non può usarlo:
        */ @Query("SELECT o FROM Order o WHERE o.status = 'PENDING' ORDER BY
        o.createdAt ASC") List<Order> findPendingOrders(Pageable pageable);
```
