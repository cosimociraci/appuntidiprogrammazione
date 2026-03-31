---
layout: post
title: "Monitoring Replication Lag (LSN Algebra)"
date: 2026-03-31 16:39:58 
tech: db
tags: ['db', 'advanced replication & ha']
pdf_file: "monitoring-replication-lag-lsn-algebra.pdf"
---

## Esigenza Reale
Verificare in tempo reale se il database di disaster recovery è allineato a quello di produzione prima di autorizzare un aggiornamento applicativo.

## Analisi Tecnica
Problema: I secondi di lag sono una metrica ingannevole: una replica può essere "a 0 secondi" ma avere megabyte di dati non ancora processati in coda. Perché: Calcolo il lag basandomi sulla differenza di byte. Ho scelto questa metrica perché è assoluta e mi dice esattamente quanta "distanza" separa i due nodi in termini di record scritti.

## Esempio Implementativo

```db
/* Query completa di analisi lag sul Master */ SELECT application_name, pg_wal_lsn_diff(pg_current_wal_lsn(), sent_lsn) AS network_lag_bytes, pg_wal_lsn_diff(sent_lsn, write_lsn) AS write_lag_bytes, pg_wal_lsn_diff(flush_lsn, replay_lsn) AS apply_lag_bytes, pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS total_lag_bytes, round(pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) / 1024.0 / 1024.0, 2) AS total_lag_mb FROM pg_stat_replication ORDER BY total_lag_bytes DESC; /* Soglia di allerta pre-deploy: blocca se lag > 5 MB */ DO $$ DECLARE lag_mb NUMERIC; BEGIN SELECT round(pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) / 1024.0 / 1024.0, 2) INTO lag_mb FROM pg_stat_replication WHERE application_name = 'dr_replica'; IF lag_mb > 5 THEN RAISE EXCEPTION 'Deploy bloccato: replica DR ha % MB di lag', lag_mb; ELSE RAISE NOTICE 'Replica allineata: % MB. Deploy autorizzato.', lag_mb; END IF; END $$;
```
