---
layout: post
title: "Lock Monitoring & Diagnosis"
date: 2026-03-31 17:04:42 
sintesi: "In un sistema di produzione, i lock "silenziosi" sono i peggiori nemici delle performance. Una transazione dimenticata aperta può bloccare l'intero sistema (es. un VACUUM o una migrazione di schema). È fondamentale avere una vista chiara di chi sta b"
tech: db
tags: ['db', 'concorrenza e locking approfond']
pdf_file: "lock-monitoring-diagnosis.pdf"
---

## Esigenza Reale
Identificare immediatamente quale script di reportistica notturno sta impedendo l'aggiornamento dei prezzi nel modulo e-commerce.

## Analisi Tecnica
Problema: Difficoltà nel distinguere tra un normale tempo di esecuzione e un'attesa forzata da un lock acquisito da un altro utente. Perché: Interrogo pg_blocking_pids. Ho scelto di mappare i PID bloccanti per visualizzare l'albero delle dipendenze e capire l'origine esatta del blocco.

## Esempio Implementativo

```db
/* Questa query mi restituisce il PID che blocca, la query in esecuzione, e la durata del blocco. È il mio strumento di debugging principale in produzione. */ SELECT bl.pid AS blocked_pid, bl.query AS blocked_query, a.pid AS blocking_pid, a.query AS blocking_query, a.xact_start AS blocking_since, now() - a.xact_start AS blocking_duration, a.state AS blocking_state FROM pg_catalog.pg_stat_activity bl JOIN pg_catalog.pg_stat_activity a ON a.pid = ANY(pg_blocking_pids(bl.pid)) WHERE bl.wait_event_type = 'Lock' ORDER BY blocking_duration DESC NULLS LAST; /* Se individuo una sessione 'idle in transaction' da troppo tempo, la termino chirurgicamente senza riavviare il server. */ SELECT pg_terminate_backend(blocking_pid) FROM ( SELECT unnest(pg_blocking_pids(pid)) AS blocking_pid FROM pg_stat_activity WHERE wait_event_type = 'Lock' ) sub WHERE ( SELECT now() - xact_start FROM pg_stat_activity WHERE pid = blocking_pid ) > interval '5 minutes'; /* Per prevenire il problema sistemicamente, imposto nel file postgresql.conf: idle_in_transaction_session_timeout = '5min' */
```
