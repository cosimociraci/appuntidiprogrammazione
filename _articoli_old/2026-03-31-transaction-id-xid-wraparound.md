---
layout: post
title: "Transaction ID (XID) Wraparound"
date: 2026-03-31 10:11:47 +0200
sintesi: "Ogni transazione in Postgres riceve un ID numerico a 32 bit. Poiché i numeri finiscono (circa 4 miliardi), Postgres deve riutilizzarli. Se non gestito..."
tech: db
tags: ['db', 'concorrenza e locking approfond']
---
## Esigenza Reale
Prevenire il blocco totale di un database di data-logging che genera milioni di transazioni al giorno.

## Analisi Tecnica
Problema: Esaurimento dei numeri identificativi delle transazioni, che renderebbe i dati storici illeggibili. Perché: Monitoro datfrozenxid. Ho scelto di automatizzare il controllo dell'età delle transazioni per forzare un VACUUM FREEZE prima di raggiungere la soglia critica del 70% dei bit disponibili.

## Esempio Implementativo

```sql
/* Verifico la distanza dal wraparound per ogni database. Se 'age' si avvicina a 2 miliardi, Postgres entrerà in modalità di sola lettura di emergenza. La soglia di allarme deve essere fissata intorno a 1.5 miliardi (75%). */ SELECT datname, age(datfrozenxid) AS xid_age, round(100.0 * age(datfrozenxid) / 2000000000, 2) AS pct_used FROM pg_database ORDER BY xid_age DESC; /* Identifico le tabelle più "anziane" che non sono state congelate di recente. Sono i candidati prioritari per un VACUUM FREEZE manuale. */ SELECT relname, age(relfrozenxid) AS table_xid_age, n_dead_tup, last_vacuum, last_autovacuum FROM pg_stat_user_tables ORDER BY table_xid_age DESC LIMIT 10; /* Forzo il congelamento sulle tabelle critiche durante una finestra di manutenzione. FREEZE marca le righe come permanentemente visibili, azzerando il contatore di età per quella tabella. */ VACUUM (FREEZE, ANALYZE, VERBOSE) log_events; /* Nel file postgresql.conf, configuro l'autovacuum in modo aggressivo per database ad alta frequenza transazionale: autovacuum_freeze_max_age = 500000000 -- Forza freeze a 500M XID autovacuum_vacuum_cost_delay = '2ms' -- Riduco la pausa tra le fasi del vacuum */ /* Implemento un job di monitoraggio (es. in Spring Scheduler) che lancia un alert se xid_age supera 1 miliardo: @Scheduled(cron = "0 0 * * * *") public void checkXidAge() { long age = jdbcTemplate.queryForObject( "SELECT max(age(datfrozenxid)) FROM pg_database", Long.class); if (age > 1_000_000_000L) { alertService.send("CRITICO: XID age al " + (age/20000000) + "%"); } } */
```