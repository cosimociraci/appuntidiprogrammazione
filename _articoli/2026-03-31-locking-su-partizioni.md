---
layout: post
title: "Locking su Partizioni"
date: 2026-03-31 16:39:58 
tech: db
tags: ['db', 'concorrenza e locking approfond']
pdf_file: "locking-su-partizioni.pdf"
---

## Esigenza Reale
Eseguire il "detach" di una partizione di log vecchia di un anno senza interrompere l'inserimento dei nuovi log di oggi.

## Analisi Tecnica
Problema: Un lock eccessivo sulla tabella master impedisce l'accesso a tutte le sottotabelle, anche se fisicamente separate. Perché: Uso ALTER TABLE ... DETACH PARTITION CONCURRENTLY. Ho scelto la modalità concurrent perché evita di prendere un Access Exclusive Lock sulla tabella padre, permettendo il traffico dati durante l'operazione.

## Esempio Implementativo

```db
/* Verifico prima la struttura delle partizioni esistenti per identificare quella da rimuovere. */ SELECT inhrelid::regclass AS partition_name, pg_get_expr(c.relpartbound, c.oid) AS partition_bound FROM pg_inherits JOIN pg_class c ON inhrelid = c.oid WHERE inhparent = 'log_data'::regclass ORDER BY partition_bound; /* Distacco la partizione vecchia senza bloccare i nuovi inserimenti. CONCURRENTLY è un'operazione in due fasi: prima marca la partizione come "detaching", poi completa il distacco quando tutte le transazioni attive sono concluse. */ ALTER TABLE log_data DETACH PARTITION log_data_2023_01 CONCURRENTLY; /* Verifico lo stato dell'operazione: durante il distacco CONCURRENTLY, la partizione è visibile in pg_partitioned_table con stato 'd'. */ SELECT relname, pg_get_expr(relpartbound, oid) FROM pg_class WHERE relname = 'log_data_2023_01'; /* Una volta distaccata, la partizione diventa una tabella indipendente. Posso archiviarla o eliminarla in modo completamente asincrono rispetto al traffico sulla tabella principale. */ -- pg_dump -t log_data_2023_01 mydb > archivio_2023_01.sql -- DROP TABLE log_data_2023_01;
```
