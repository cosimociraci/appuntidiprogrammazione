---
layout: post
title: "B-Tree Index Bloat & Fillfactor"
date: 2026-03-31 10:11:47 +0200
sintesi: "Gli indici B-Tree tendono a frammentarsi (bloat) a causa di frequenti update e delete, poiché PostgreSQL non può riutilizzare immediatamente lo spazio..."
tech: db
tags: ['db', 'indexing internals']
---
## Esigenza Reale
Mantenere alte le performance di ricerca su una tabella di "sessioni attive" che subisce migliaia di cancellazioni e inserimenti al minuto.

## Analisi Tecnica
Problema: Il degrado delle performance dovuto alla frammentazione fisica dell'indice che costringe a scansioni di pagine quasi vuote. Perché: Ho scelto di abbassare il fillfactor. In questo modo permetto a Postgres di inserire nuove versioni delle chiavi nella stessa pagina, riducendo l'overhead di riorganizzazione dell'albero.

## Esempio Implementativo

```sql
/* Creo un indice con spazio di riserva per gli update. Il fillfactor=85 lascia il 15% di ogni pagina libero per aggiornamenti futuri, prevenendo la frammentazione precoce sotto carichi di scrittura intensi. */ CREATE INDEX idx_sessions_updated_at ON sessions (updated_at) WITH (fillfactor = 85); /* Per una tabella esistente, modifico il fillfactor e ricostruisco l'indice in modo non bloccante: */ ALTER INDEX idx_sessions_updated_at SET (fillfactor = 85); REINDEX INDEX CONCURRENTLY idx_sessions_updated_at; /* Monitoro il livello di bloat corrente con pgstatindex per decidere se e quando intervenire: */ SELECT * FROM pgstatindex('idx_sessions_updated_at'); /* Leggo i campi chiave: avg_leaf_density: idealmente > 70%. Se scende sotto il 50%, il bloat è significativo. leaf_fragmentation: percentuale di pagine foglia fuori ordine. leaf_pages: numero totale di pagine foglia dell'indice. */ /* Verifico il bloat aggregato su tutti gli indici della tabella sessions: */ SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid)) AS index_size, idx_scan, idx_tup_read, idx_tup_fetch FROM pg_stat_user_indexes WHERE relname = 'sessions' ORDER BY pg_relation_size(indexrelid) DESC; /* Se il bloat è già elevato, eseguo un REINDEX CONCURRENTLY per ricostruire l'indice senza bloccare le query in produzione: */ REINDEX INDEX CONCURRENTLY idx_sessions_updated_at; /* Per la tabella sessions con carico misto (insert + delete intensi), imposto anche il fillfactor sulla tabella stessa per facilitare gli HOT update (Heap Only Tuple): */ ALTER TABLE sessions SET (fillfactor = 85); /* In Spring Boot, schedulo un job settimanale che controlla il bloat e lancia il REINDEX se necessario: @Scheduled(cron = "0 0 3 * * SUN") public void checkIndexBloat() { Double density = jdbcTemplate.queryForObject( "SELECT avg_leaf_density FROM pgstatindex('idx_sessions_updated_at')", Double.class); if (density != null && density < 50.0) { jdbcTemplate.execute("REINDEX INDEX CONCURRENTLY idx_sessions_updated_at"); log.warn("REINDEX eseguito: avg_leaf_density era {}", density); } } */
```