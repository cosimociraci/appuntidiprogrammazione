---
layout: post
title: TOAST Storage Strategies
date: '2026-03-31 16:25:01 '
sintesi: 'Quando una colonna supera i 2KB (es. testi lunghi o JSONB), Postgres usa
  il sistema TOAST (The Oversized-Attribute Storage Technique) per spostarla in una
  tabella separata "fuori riga". Esistono diverse strategie: EXTENDED (compressione
  + fuori riga)'
esigenza: Migliorare la velocità di accesso a documenti JSONB di medie dimensioni
  che vengono letti in quasi tutte le query della dashboard.
tech: db
tags:
- db
- vacuum & storage
codice: '/* Verifico la strategia TOAST attuale di tutte le colonne della tabella
  */ SELECT attname, attstorage FROM pg_attribute WHERE attrelid = ''documents''::regclass
  AND attnum > 0; /* ''x'' = EXTENDED (default), ''p'' = PLAIN, ''m'' = MAIN, ''e''
  = EXTERNAL */ /* Cambio la strategia in MAIN per la colonna metadata */ ALTER TABLE
  documents ALTER COLUMN metadata SET STORAGE MAIN; /* La modifica non riscrive le
  righe esistenti: diventa effettiva solo per i nuovi insert/update */ /* Forzo la
  riscrittura delle righe esistenti per applicare subito il cambio */ UPDATE documents
  SET metadata = metadata WHERE id IN (SELECT id FROM documents LIMIT 10000); /* Verifico
  la dimensione della tabella TOAST prima e dopo per misurare l''impatto */ SELECT
  pg_size_pretty(pg_total_relation_size(''pg_toast.pg_toast_'' || relfilenode::text))
  AS toast_size FROM pg_class WHERE relname = ''documents'';'
---

Problema: Latenza extra introdotta dal recupero dei dati dai chunk della tabella TOAST esterna. Perché: Cambio la storage strategy in MAIN. Ho scelto questa tecnica per mantenere i dati vicini alla riga principale, riducendo il numero di letture I/O necessarie per ricostruire l'oggetto.