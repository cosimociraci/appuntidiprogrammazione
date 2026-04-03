---
layout: post
title: "GIN Index e Pending List Tuning"
date: 2026-04-03 14:45:19
sintesi: >
  Gli indici GIN (Generalized Inverted Index) sono fondamentali per la ricerca Full Text e per i campi JSONB, ma sono notoriamente lenti in fase di inserimento perché ogni riga genera molteplici voci nell'indice. Il ruolo della pending_list è centrale:
tech: "db"
tags: ["db", "indexing internals"]
pdf_file: "gin-index-e-pending-list-tuning.pdf"
---

## Esigenza Reale
Ottimizzare l'indicizzazione di un flusso massivo di log applicativi salvati in formato JSONB per analisi in tempo reale.

## Analisi Tecnica
Problema: Latenza in scrittura inaccettabile dovuta al continuo aggiornamento della struttura ad albero invertito dell'indice GIN. Perché: Ho aumentato il buffer della pending list. Ho scelto di accumulare più dati in memoria prima di scrivere sul disco, trasformando tanti piccoli aggiornamenti casuali in un'unica operazione sequenziale efficiente.

## Esempio Implementativo

```sql
* Creo l'indice GIN con fastupdate abilitato e una pending list generosa per
* ingestione massiva di log JSONB. */
 CREATE INDEX CONCURRENTLY idx_app_logs_gin ON app_logs USING GIN (payload
jsonb_path_ops) WITH (fastupdate = on, gin_pending_list_limit = 16384); -- 16MB
/* Modifico il limite sulla tabella esistente senza ricreare l'indice: */
 ALTER TABLE app_logs SET (gin_pending_list_limit = 16384); ANALYZE app_logs; 
* Verifico la dimensione attuale della pending list e la dimensione totale
* dell'indice: */
 SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes WHERE relname = 'app_logs' AND indexrelname =
'idx_app_logs_gin';
* Forzo manualmente il merge della pending list nell'indice principale (utile
* dopo un bulk insert): */
 SELECT gin_clean_pending_list('idx_app_logs_gin'::regclass); 
* Confronto il comportamento di scrittura con fastupdate on vs off su un batch
* di 10.000 inserimenti: */
 -- Con fastupdate = on: ogni INSERT scrive solo nella lista pendente (veloce)
-- Con fastupdate = off: ogni INSERT aggiorna direttamente l'albero GIN (lento
ma ricerche sempre coerenti)
* Per bulk import, disabilito temporaneamente fastupdate per evitare che la
* pending list esploda e produca un merge gigante a fine operazione: */
 ALTER INDEX idx_app_logs_gin SET (fastupdate = off); -- Eseguo il bulk insert
COPY app_logs FROM '/data/logs_import.csv' WITH (FORMAT csv); ALTER INDEX
idx_app_logs_gin SET (fastupdate = on); REINDEX INDEX CONCURRENTLY
idx_app_logs_gin;
* In Spring Boot, per l'ingestione continua di log uso un buffer applicativo che
* accumula 500 record prima di fare un INSERT batch, riducendo ulteriormente la
* pressione sulla pending list: @Transactional public void
* flushLogBuffer(List<AppLog> buffer)
{ if (buffer.size() >= 500) 
{ logRepository.saveAll(buffer); buffer.clear(); }
 }
 */
```
