---
layout: post
title: "Tuning del Random Page Cost"
date: 2026-03-31 19:22:02 
sintesi: "Il Planner di PostgreSQL stima il costo delle scansioni degli indici basandosi sul parametro random_page_cost. Per impostazione predefinita, questo valore è 4.0, un retaggio dell'era dei dischi rotanti (HDD) dove l'accesso casuale era molto più lento"
tech: db
tags: [db, "query opt. & planner"]
pdf_file: "tuning-del-random-page-cost.pdf"
---

## Esigenza Reale
Ottimizzare le performance di un database migrato da un vecchio server fisico a un'istanza Cloud con storage SSD ad alte prestazioni.

## Analisi Tecnica
Problema: Il Planner evita l'uso degli indici perché sovrastima il costo di lettura delle pagine sparse sul disco. Perché: Ho deciso di allineare random_page_cost a seq_page_cost. In questo modo elimino il bias contro gli indici, riflettendo la realtà fisica dell'hardware SSD dove la latenza di seek è trascurabile.

## Esempio Implementativo

```db
/* Testo l'impatto del parametro solo per la sessione corrente, senza toccare la
* configurazione globale del server. In questo modo posso confrontare i piani
* prima e dopo in modo sicuro. */ SET random_page_cost = 1.1; /* Eseguo la
* stessa query con e senza il parametro modificato e confronto i piani. Con il
* valore di default 4.0 probabilmente vedrò un Seq Scan. Con 1.1 mi aspetto un
* Index Scan o un Bitmap Index Scan. */ EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM
* big_data WHERE category_id = 500; /* Per rendere la modifica permanente e
* globale, agisco su postgresql.conf (richiede reload, non restart):
* random_page_cost = 1.1 -- Per SSD/NVMe effective_cache_size = '12GB' -- Aiuto
* il Planner a capire quanta RAM è disponibile per il caching Se uso storage
* NVMe estremamente veloce, posso scendere anche a 1.0: random_page_cost = 1.0
* seq_page_cost = 1.0 */ /* Verifico il tipo di storage effettivo prima di
* decidere il valore: un disco rotante con RAID non beneficia di questo
* abbassamento. */ SELECT name, setting, unit FROM pg_settings WHERE name IN
* ('random_page_cost', 'seq_page_cost', 'effective_cache_size'); /* A livello di
* singola tabella critica, posso sovrascrivere il parametro globale con un
* valore specifico per quella relazione (Postgres 13+): */ ALTER TABLE big_data
* SET (seq_page_cost = 1, random_page_cost = 1);
```
