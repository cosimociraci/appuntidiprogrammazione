---
layout: post
title: "Index Scan vs Bitmap Scan"
date: 2026-03-31 17:04:42 
sintesi: "PostgreSQL ha due modi principali di usare un indice: Index Scan (legge l'indice e va subito alla tabella riga per riga) e Bitmap Index Scan (legge tutto l'indice, crea una mappa di bit delle righe e poi accede alla tabella in modo ordinato). Il Bitm"
tech: db
tags: ['db', 'query opt. & planner']
pdf_file: "index-scan-vs-bitmap-scan.pdf"
---

## Esigenza Reale
Ottimizzare query che filtrano per categorie non troppo selettive (es. tutti gli ordini "In lavorazione").

## Analisi Tecnica
Problema: L'accesso casuale alla tabella tramite Index Scan diventa inefficiente se le righe da recuperare sono migliaia. Perché: Il database sceglie il Bitmap Scan. Ho accettato questo piano perché riduce il numero di IOPS casuali raggruppando gli accessi alla tabella.

## Esempio Implementativo

```db
/* Osservo il tipo di scan scelto dal Planner. Con una colonna a bassa selettività come status, mi aspetto un Bitmap Heap Scan preceduto da un Bitmap Index Scan. */ EXPLAIN (ANALYZE, BUFFERS) SELECT user_id, created_at, total FROM orders WHERE status = 'shipped'; /* L'output avrà questa struttura: -> Bitmap Heap Scan on orders (rows=15420) Recheck Cond: (status = 'shipped') -> Bitmap Index Scan on idx_orders_status Index Cond: (status = 'shipped') Il "Recheck" avviene perché il bitmap usa la granularità della pagina, non della riga: quando recupera la pagina, deve riverificare la condizione su ogni riga della pagina. */ /* Se il Bitmap Scan è lento per via degli accessi alla heap, creo un indice coprente che elimina la necessità di toccare la tabella: */ CREATE INDEX CONCURRENTLY idx_orders_status_covering ON orders (status) INCLUDE (user_id, created_at, total); /* In alternativa, se voglio forzare l'ordine fisico della tabella per allinearlo all'indice e rendere i Bitmap Scan quasi sequenziali: */ CLUSTER orders USING idx_orders_status_covering; /* Forzo il CLUSTER periodicamente tramite un job di manutenzione, perché i nuovi inserimenti non mantengono l'ordine fisico: */ VACUUM ANALYZE orders; /* Verifico quando è stata eseguita l'ultima operazione di clustering: */ SELECT relname, reltuples, relpages FROM pg_class WHERE relname = 'orders'; /* Per decidere tra Index Scan e Bitmap Scan, Postgres usa la soglia effective_cache_size. Se la tabella è interamente in cache, preferisce Index Scan anche per molte righe. */ SET effective_cache_size = '8GB'; -- Rifletto la RAM reale disponibile per il caching
```
