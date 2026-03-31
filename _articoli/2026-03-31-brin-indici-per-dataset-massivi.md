---
layout: post
title: "BRIN: Indici per dataset massivi"
date: 2026-03-31 16:39:58 
tech: db
tags: ['db', 'indexing internals']
pdf_file: "brin-indici-per-dataset-massivi.pdf"
---

## Esigenza Reale
Gestire l'indicizzazione di tabelle di telemetria IoT che crescono di 500 milioni di righe al mese con un overhead di storage minimo.

## Analisi Tecnica
Problema: L'indice B-Tree standard consuma troppo spazio disco e satura la cache, rallentando l'intero sistema. Perché: Ho optato per BRIN. Ho scelto questa soluzione perché i log arrivano in ordine cronologico, permettendo a BRIN di escludere il 99% dei blocchi disco con una frazione dello spazio di un B-Tree.

## Esempio Implementativo

```db
/* Creo un indice BRIN su una colonna timestamp. pages_per_range=64 significa che ogni voce dell'indice copre 64 pagine (512KB con block_size=8KB): più piccolo = più preciso ma indice più grande. */ CREATE INDEX idx_telemetry_brin ON telemetry_data USING BRIN (recorded_at) WITH (pages_per_range = 64); /* Confronto la dimensione con un B-Tree equivalente: */ SELECT pg_size_pretty(pg_relation_size('idx_telemetry_brin')) AS brin_size; -- Es: 48 kB -- CREATE INDEX idx_telemetry_btree ON telemetry_data (recorded_at); -- SELECT pg_size_pretty(pg_relation_size('idx_telemetry_btree')) AS btree_size; -- Es: 4200 MB /* Verifico la correlazione fisica della colonna per confermare che BRIN sia adatto: un valore vicino a 1.0 o -1.0 indica dati ordinati e BRIN sarà efficace. */ SELECT attname, correlation FROM pg_stats WHERE tablename = 'telemetry_data' AND attname = 'recorded_at'; /* Eseguo una query su un intervallo temporale e verifico che BRIN elimini la maggior parte dei blocchi: */ EXPLAIN (ANALYZE, BUFFERS) SELECT device_id, value FROM telemetry_data WHERE recorded_at BETWEEN '2026-03-01' AND '2026-03-07'; /* Nell'output cerco "Lossy" e "pages_removed": un alto numero di pagine rimosse indica che BRIN sta lavorando bene. */ /* Se nel tempo i dati vengono inseriti fuori ordine (es. dati in ritardo da sensori offline), aggiorno il riepilogo BRIN manualmente: */ SELECT brin_summarize_new_values('idx_telemetry_brin'::regclass); /* Per trovare il pages_per_range ottimale, testo diversi valori e misuro il rapporto tra dimensione indice e pagine escluse nelle query tipiche: */ CREATE INDEX idx_telemetry_brin_32 ON telemetry_data USING BRIN (recorded_at) WITH (pages_per_range = 32); CREATE INDEX idx_telemetry_brin_128 ON telemetry_data USING BRIN (recorded_at) WITH (pages_per_range = 128); /* In Spring Boot, per tabelle IoT uso sempre BRIN sulle colonne temporali e B-Tree solo su device_id per i lookup puntuali: */ -- CREATE INDEX idx_telemetry_device ON telemetry_data (device_id); -- B-Tree per lookup puntuale -- CREATE INDEX idx_telemetry_brin ON telemetry_data USING BRIN (recorded_at); -- BRIN per range temporali
```
