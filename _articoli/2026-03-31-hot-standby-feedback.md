---
layout: post
title: "Hot Standby Feedback"
date: 2026-03-31 19:22:01 
sintesi: "In una configurazione Master-Replica, può succedere che una query lunga sulla replica venga interrotta perché il Master ha rimosso dei dati (tramite Vacuum) che la replica deve ancora processare. Questo è il replication conflict. Il meccanismo hot_st"
tech: db
tags: [db, "concorrenza e locking approfond"]
pdf_file: "hot-standby-feedback.pdf"
---

## Esigenza Reale
Evitare che i report di fine mese eseguiti sulla replica falliscano a causa dell'attività di pulizia del database principale.

## Analisi Tecnica
Problema: Disallineamento tra la pulizia dei dati (Vacuum) sul Master e le necessità di lettura delle transazioni aperte sulla Replica. Perché: Attivo hot_standby_feedback = on. Ho scelto di accettare un po' di spazio extra occupato sul Master pur di garantire la stabilità dei report sulla Replica.

## Esempio Implementativo

```db
/* Configurazione da applicare nel file postgresql.conf della REPLICA. Comunica
* al master di mantenere le tuple necessarie finché la replica non ha concluso
* le sue transazioni aperte. */ -- hot_standby_feedback = on --
* max_standby_streaming_delay = '30s' /* Sul MASTER, monitoro il bloat causato
* da hot_standby_feedback controllando lo slot di replica e il ritardo
* accumulato. Se il ritardo cresce troppo, il Master trattiene versioni vecchie
* per un tempo eccessivo. */ SELECT slot_name, active,
* pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS
* retained_wal, catalog_xmin, age(catalog_xmin) AS catalog_xmin_age FROM
* pg_replication_slots; /* Sul MASTER, verifico che l'autovacuum non venga
* bloccato dalla replica per troppo tempo. Se 'catalog_xmin_age' supera soglie
* critiche, valuto di disabilitare temporaneamente il feedback. */ SELECT now()
* - pg_last_xact_replay_timestamp() AS replication_lag FROM pg_stat_replication;
* /* Strategia di bilanciamento: invece di hot_standby_feedback globale, posso
* usare max_standby_streaming_delay per definire quanto a lungo la replica
* tolera il ritardo prima di cancellare la query piuttosto che aspettare il
* master: -- Sul master in postgresql.conf: wal_keep_size = '2GB' -- Mantiene
* abbastanza WAL per query lunghe -- Sulla replica: max_standby_streaming_delay
* = '10min' hot_standby_feedback = on */ /* A livello applicativo, instrumento i
* report lunghi con un timeout esplicito sulla connessione replica per evitare
* che una query infinita blocchi il feedback indefinitamente: SET
* statement_timeout = '25min'; SET idle_in_transaction_session_timeout = '5min';
* */
```
