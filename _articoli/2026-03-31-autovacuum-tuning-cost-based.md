---
layout: post
title: "Autovacuum Tuning (Cost-Based)"
date: 2026-03-31 16:39:58 
tech: db
tags: ['db', 'vacuum & storage']
pdf_file: "autovacuum-tuning-cost-based.pdf"
---

## Esigenza Reale
Evitare che una tabella di log da 500GB diventi lenta a causa dell'accumulo di milioni di record eliminati che il vacuum non riesce a processare in tempo.

## Analisi Tecnica
Problema: Il Vacuum è troppo lento rispetto alla velocità di generazione delle dead tuples, causando il "bloat" della tabella. Perché: Ho alzato il budget di costo e ridotto il delay. Ho scelto di dare più priorità all'I/O di manutenzione per garantire che lo spazio venga riutilizzato immediatamente, evitando l'espansione indefinita del file su disco.

## Esempio Implementativo

```db
/* Regolo i parametri per rendere il vacuum più aggressivo sulla tabella critica, senza toccare i default dell'intero cluster */ ALTER TABLE high_traffic_table SET (autovacuum_vacuum_cost_limit = 1000, autovacuum_vacuum_cost_delay = 10); /* Verifico che i nuovi parametri siano applicati */ SELECT reloptions FROM pg_class WHERE relname = 'high_traffic_table'; /* Monitoro il progresso in tempo reale durante un vacuum manuale */ VACUUM (VERBOSE, ANALYZE) high_traffic_table; /* Controllo quante dead tuples si accumulano nel tempo: se n_dead_tup cresce più veloce del vacuum, alzo ancora il limite */ SELECT relname, n_live_tup, n_dead_tup, last_autovacuum, last_autoanalyze FROM pg_stat_user_tables WHERE relname = 'high_traffic_table'; /* Se necessario, forzo un vacuum manuale fuori orario di punta */ VACUUM ANALYZE high_traffic_table;
```
