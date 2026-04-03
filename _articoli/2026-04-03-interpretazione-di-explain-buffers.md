---
layout: post
title: "Interpretazione di EXPLAIN BUFFERS"
date: 2026-04-03 14:45:17
sintesi: >
  La metrica più onesta per misurare una query non è il tempo (che dipende dal carico del server), ma i blocchi letti (BUFFERS). La differenza tra shared hit (dati in RAM), read (dati letti dal disco) e dirtied (pagine modificate) rivela l'impatto real
tech: "db"
tags: ["db", "query opt. & planner"]
pdf_file: "interpretazione-di-explain-buffers.pdf"
---

## Esigenza Reale
Diagnosticare perché una query è veloce a volte e lenta altre (spesso dovuto alla presenza o meno dei dati nel buffer cache).

## Analisi Tecnica
Problema: La latenza variabile delle query rende difficile capire se l'ottimizzazione sta funzionando davvero. Perché: Uso BUFFERS. Ho scelto di basarmi sul numero di pagine toccate perché è un valore costante che non dipende dal "calore" della cache al momento del test.

## Esempio Implementativo

```sql
* Eseguo la query con BUFFERS per vedere il comportamento reale sull'I/O. La
* prima esecuzione avrà molti 'read' (cold cache), la seconda avrà molti 'hit'
* (warm cache). */
 EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT * FROM logs WHERE created_at >
now() - interval '1 day';
* Leggo l'output in questo modo: shared hit=1200 -> 1200 blocchi da 8KB letti
* dalla RAM (ottimo) shared read=3400 -> 3400 blocchi letti dal disco (da
* ridurre) shared dirtied=50 -> 50 pagine modificate in memoria (normale per
* DML) shared written=10 -> 10 pagine scritte su disco dal bgwriter durante la
* query (segnale di pressione su shared_buffers) */
 
* Se shared read è alto, ho due strade: 1) Creo un indice per ridurre il numero
* totale di pagine toccate. 2) Aumento shared_buffers in postgresql.conf per
* tenere più dati in RAM. */
 -- Soluzione 1: indice parziale che copre solo i log recenti CREATE INDEX
CONCURRENTLY idx_logs_recent ON logs (created_at) WHERE created_at >
'2026-01-01';
* Per svuotare la cache di sistema e testare il comportamento a cold start (solo
* su ambienti di test, mai in produzione): */
 -- pg_ctl stop -- sync && echo 3 > /proc/sys/vm/drop_caches -- pg_ctl start 
* In produzione, confronto il rapporto hit/read nel tempo tramite
* pg_statio_user_tables per identificare tabelle che non stanno beneficiando
* della cache: */
 SELECT relname, heap_blks_hit, heap_blks_read, round(100.0 * heap_blks_hit /
nullif(heap_blks_hit + heap_blks_read, 0), 2) AS cache_hit_pct FROM
pg_statio_user_tables ORDER BY heap_blks_read DESC LIMIT 10;
```
