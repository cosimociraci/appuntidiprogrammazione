---
layout: post
title: "Logical Decoding & Replication Slots"
date: 2026-03-31 17:04:42 
sintesi: "La replica logica permette di trasmettere solo le modifiche ai dati (INSERT/UPDATE/DELETE) invece di interi blocchi di disco. Il problema principale sorge quando il ricevente (subscriber) si disconnette: il mittente (publisher) deve conservare tutti "
tech: db
tags: ['db', 'advanced replication & ha']
pdf_file: "logical-decoding-replication-slots.pdf"
---

## Esigenza Reale
Sincronizzare tabelle specifiche tra un database di produzione e un database di data-warehouse per analisi in tempo reale senza replicare l'intero cluster.

## Analisi Tecnica
Problema: Rischio di saturazione del disco sul nodo primario se i subscriber non confermano la ricezione dei dati. Perché: Uso i Logical Replication Slots. Ho scelto questa strada perché garantisce "zero data loss" nella sincronizzazione, a patto di avere un sistema di monitoring che elimina i slot inattivi da troppo tempo.

## Esempio Implementativo

```db
/* Sul Publisher: creo una pubblicazione per tabelle specifiche, evitando di replicare l'intero database verso il data warehouse. */ CREATE PUBLICATION subset_pub FOR TABLE orders, customers, products; /* Sul Subscriber (data warehouse): creo la subscription che si connette al publisher e inizia a ricevere le modifiche. */ CREATE SUBSCRIPTION dw_sub CONNECTION 'host=prod_db port=5432 dbname=myapp user=rep_user password=secret' PUBLICATION subset_pub; /* Monitoro continuamente lo stato degli slot sul Publisher. Se 'active' è false da più di 30 minuti e 'confirmed_flush_lsn' non avanza, il subscriber è probabilmente morto e il disco si sta riempiendo. */ SELECT slot_name, slot_type, active, pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)) AS retained_wal, confirmed_flush_lsn FROM pg_replication_slots WHERE slot_type = 'logical'; /* Se uno slot inattivo sta trattenendo troppo WAL, lo elimino per proteggere il disco del publisher: */ SELECT pg_drop_replication_slot('dw_sub'); /* Imposto un limite massimo di slot e una soglia di WAL trattenuto nel postgresql.conf: max_replication_slots = 10 wal_keep_size = '1GB' -- Limite di WAL locale prima di allertare */ /* In Spring Boot, schedulo un job che monitora i slot e invia un alert se il WAL trattenuto supera una soglia critica: @Scheduled(cron = "0 */5 * * * *") // Ogni 5 minuti public void monitorReplicationSlots() { List<Map<String, Object>> slots = jdbcTemplate.queryForList(""" SELECT slot_name, active, pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn) AS retained_bytes FROM pg_replication_slots WHERE slot_type = 'logical' """); for (Map<String, Object> slot : slots) { long retainedBytes = ((Number) slot.get("retained_bytes")).longValue(); boolean active = (boolean) slot.get("active"); if (!active && retainedBytes > 5_000_000_000L) { // 5GB alertService.sendCritical("Slot " + slot.get("slot_name") + " inattivo trattiene " + retainedBytes / 1e9 + " GB di WAL"); } } } */
```
