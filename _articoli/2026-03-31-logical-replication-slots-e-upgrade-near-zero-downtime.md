---
layout: post
title: "Logical Replication Slots e Upgrade "Near-Zero Downtime""
date: 2026-03-31 18:55:09 
sintesi: "La replica logica è lo strumento principe per eseguire upgrade di versione (es. da PG 15 a 17) con downtime minimo. La procedura prevede: creare un nuovo cluster con la versione recente, attivare la replica logica dal vecchio al nuovo, aspettare che "
tech: db
tags: [db, "advanced replication & ha"]
pdf_file: "logical-replication-slots-e-upgrade-near-zero-downtime.pdf"
---

## Esigenza Reale
Aggiornare il database di produzione a una nuova major version senza fermare il servizio per più di 30 secondi.

## Analisi Tecnica
Problema: I metodi di upgrade tradizionali (pg_upgrade) richiedono che il database sia spento durante l'intera procedura di migrazione dei file. Perché: Uso la replica logica come ponte. Ho scelto questa tecnica perché mi permette di testare il nuovo database "caldo" con dati reali prima di migrare definitivamente il traffico.

## Esempio Implementativo

```db
/* STEP 1: Sul vecchio DB (v15) — abilitare la replica logica */ wal_level = logical; /* Nel postgresql.conf: obbligatorio, senza questo la publication non funziona */ CREATE PUBLICATION upgrade_pub FOR ALL TABLES; /* STEP 2: Sul nuovo DB (v17) — caricare lo schema prima della subscription */ pg_dump -s -h old_db -U postgres mydb | psql -h new_db -U postgres mydb /* Ho eseguito solo lo schema (-s): i dati arriveranno tramite replica logica */ /* STEP 3: Sul nuovo DB (v17) — creare la subscription */ CREATE SUBSCRIPTION upgrade_sub CONNECTION 'host=old_db port=5432 user=rep_user password=secret dbname=mydb' PUBLICATION upgrade_pub; /* STEP 4: Monitoraggio del lag fino ad allineamento */ SELECT subname, received_lsn, latest_end_lsn, pg_wal_lsn_diff(latest_end_lsn, received_lsn) AS lag_bytes FROM pg_stat_subscription; /* Attendo che lag_bytes sia 0 prima di procedere */ /* STEP 5: Sincronizzazione manuale delle sequenze — passaggio critico spesso dimenticato */ SELECT 'SELECT setval(' || quote_literal(sequence_name) || ', ' || last_value || ');' FROM information_schema.sequences JOIN (SELECT sequence_name, last_value FROM pg_sequences) s USING (sequence_name); /* Ho generato ed eseguito questi setval() sul nuovo DB prima dello switch */ /* STEP 6: Switch delle connessioni applicative (finestra di 30 secondi) */ /* Sul vecchio DB: blocco nuove scritture */ REVOKE CONNECT ON DATABASE mydb FROM app_user; SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'mydb' AND usename = 'app_user'; /* Aspetto lag_bytes = 0, poi disabilito la subscription sul nuovo DB */ ALTER SUBSCRIPTION upgrade_sub DISABLE; /* Punto le connessioni applicative al nuovo DB (v17): modifica del connection string o del load balancer */ /* STEP 7: Verifica post-switch sul nuovo DB */ SELECT version(); /* Deve restituire PostgreSQL 17.x */ SELECT count(*) FROM pg_stat_user_tables; /* Verifico che tutte le tabelle siano presenti e popolate */
```
