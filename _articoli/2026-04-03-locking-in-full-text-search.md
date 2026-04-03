---
layout: post
title: "Locking in Full Text Search"
date: 2026-04-03 14:40:26
sintesi: "La ricerca testuale (FTS) in Postgres usa indici GIN. Questi indici sono molto efficienti in lettura ma costosi da aggiornare. Durante un inserimento massivo, l'aggiornamento dell'indice GIN pu diventare un punto di contesa per i lock, poich deve i"
tech: "db"
tags: ["db", "concorrenza e locking approfond"]
pdf_file: "locking-in-full-text-search.pdf"
---

## Esigenza Reale
Velocizzare l'indicizzazione di migliaia di documenti al minuto in un motore di ricerca interno.

## Analisi Tecnica
Problema: L'aggiornamento simultaneo degli indici GIN da parte di più transazioni causa rallentamenti significativi (lock contention). Perché: Aumento la dimensione della pending list. Ho scelto di bufferizzare gli aggiornamenti dell'indice in memoria per consolidarli in operazioni batch più rare ma più efficienti.

## Esempio Implementativo

```db
* Creo l'indice GIN con l'opzione fastupdate abilitata (è il default ma lo rendo
* esplicito) e aumento il buffer della pending list per ridurre la frequenza dei
* merge sull'entry tree principale. */
 CREATE INDEX CONCURRENTLY idx_documents_fts ON documents USING GIN
(to_tsvector('italian', coalesce(title, '') || ' ' || coalesce(body, ''))) WITH
(fastupdate = on, gin_pending_list_limit = 8192); -- 8MB di buffer
* Verifico la dimensione attuale della pending list per capire se il merge viene
* triggerato troppo spesso. */
 SELECT indexrelid::regclass AS index_name,
pg_size_pretty(pg_relation_size(indexrelid)) AS index_size FROM
pg_stat_user_indexes WHERE indexrelname = 'idx_documents_fts';
* Per inserimenti massivi in batch (es. importazione iniziale), disabilito
* temporaneamente fastupdate e ricostruisco l'indice alla fine: è più veloce che
* gestire migliaia di merge intermedi. */
 ALTER INDEX idx_documents_fts SET (fastupdate = off); -- Eseguo il bulk insert
INSERT INTO documents (title, body) SELECT title, body FROM staging_documents;
-- Riabilito fastupdate e forzo un reindex pulito ALTER INDEX idx_documents_fts
SET (fastupdate = on); REINDEX INDEX CONCURRENTLY idx_documents_fts;
* Monitoro la lock contention sull'indice durante un inserimento concorrente per
* verificare il miglioramento: */
 SELECT pid, wait_event_type, wait_event, query FROM pg_stat_activity WHERE
wait_event_type = 'Lock' AND query ILIKE '%documents%';
* In Spring Boot, per l'inserimento massivo di documenti uso un executor con
* thread pool limitato per controllare la concorrenza sui lock GIN: @Autowired
* private ThreadPoolTaskExecutor taskExecutor; public void
* bulkIndex(List<Document> docs)
{ List<List<Document>> batches = Lists.partition(docs, 500);
batches.forEach(batch -> taskExecutor.execute(() ->
documentRepository.saveAll(batch))); }
 */
```
