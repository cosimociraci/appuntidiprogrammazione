---
layout: code
title: "Index Bloat e REINDEX CONCURRENTLY"
date: 2026-12-28 12:00:00
sintesi: >
  Anche gli indici soffrono di bloat, spesso più delle tabelle. Un indice frammentato rallenta tutte le query di ricerca. Postgres 12+ permette il comando REINDEX CONCURRENTLY che ricostruisce l'indice da zero senza bloccare le scritture sulla tabella.
tech: "sql"
tags: ["sql", "db", "postgresql", "spring boot"]
pdf_file: "index-bloat-e-reindex-concurrently.pdf"
---

## Esigenza Reale
Ripristinare le performance di ricerca su una tabella di messaggistica dove gli indici sono diventati tre volte più grandi dei dati reali.

## Analisi Tecnica
**Problema:** Indici massivi che non entrano più in RAM a causa della frammentazione interna, causando swap su disco.

**Perché:** Eseguo il reindex online. Ho scelto la modalità CONCURRENTLY perché non posso permettermi di fermare l'applicazione, ma ho bisogno di un indice compatto per velocizzare i join.

## Esempio Implementativo

```sql
    /* Stimo il bloat degli indici confrontando la dimensione attuale con il
        numero di tuple reali. Un indice sano ha una densità foglia superiore al
        70%: sotto il 50% il bloat è significativo. */ SELECT indexrelname,
        pg_size_pretty(pg_relation_size(indexrelid)) AS index_size, idx_scan,
        idx_tup_read, idx_tup_fetch FROM pg_stat_user_indexes WHERE relname =
        'messages' ORDER BY pg_relation_size(indexrelid) DESC; /* Per una stima
        più precisa del bloat uso pgstatindex, disponibile nell'estensione
        pgstattuple: */ CREATE EXTENSION IF NOT EXISTS pgstattuple; SELECT *
        FROM pgstatindex('idx_messages_user_id'); /* Leggo i campi chiave:
        avg_leaf_density < 50% -> bloat critico, intervenire subito
        leaf_fragmentation alto -> le pagine foglia sono fuori ordine fisico
        leaf_pages -> numero totale di pagine foglia dell'indice */ /*
        Ricostruisco l'indice in background senza bloccare INSERT/UPDATE/DELETE.
        CONCURRENTLY crea un nuovo indice in parallelo e sostituisce il vecchio
        atomicamente. */ REINDEX INDEX CONCURRENTLY idx_messages_user_id; /*
        Verifico la riduzione di dimensione dopo il reindex confrontando prima e
        dopo: */ SELECT pg_size_pretty(pg_relation_size('idx_messages_user_id'))
        AS new_size; /* Per ricostruire tutti gli indici di una tabella in un
        colpo solo senza downtime: */ REINDEX TABLE CONCURRENTLY messages; /*
        Identifico sistematicamente tutti gli indici del database con bloat
        critico per prioritizzare gli interventi: */ SELECT schemaname,
        tablename, indexname, pg_size_pretty(pg_relation_size(indexrelid)) AS
        current_size, idx_scan FROM pg_stat_user_indexes WHERE
        pg_relation_size(indexrelid) > 100 * 1024 * 1024 -- Solo indici > 100MB
        AND idx_scan < 100 -- Poco usati: candidati anche alla rimozione ORDER
        BY pg_relation_size(indexrelid) DESC; /* Automatizzo il reindex mensile
        tramite pg_cron per gli indici delle tabelle ad alta rotazione: */
        CREATE EXTENSION IF NOT EXISTS pg_cron; SELECT
        cron.schedule('reindex-messages-monthly', '0 3 1 * *', 'REINDEX TABLE
        CONCURRENTLY messages'); /* Verifico i job schedulati: */ SELECT jobid,
        schedule, command, active FROM cron.job WHERE command LIKE '%REINDEX%';
        /* In Spring Boot, per ambienti senza pg_cron, schedulo il reindex
        tramite un job Spring che lo esegue durante la finestra di manutenzione
        notturna: @Scheduled(cron = "0 0 3 1 * *") // Ogni primo del mese alle
        03:00 public void reindexCriticalTables() { List<String> indexes =
        List.of( "idx_messages_user_id", "idx_messages_created_at",
        "idx_messages_conversation_id" ); for (String idx : indexes) {
        log.info("Avvio REINDEX CONCURRENTLY su {}", idx);
        jdbcTemplate.execute("REINDEX INDEX CONCURRENTLY " + idx);
        log.info("REINDEX completato su {}", idx); } } */
```
