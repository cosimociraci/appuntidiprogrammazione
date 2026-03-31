---
layout: post
title: "FSM e VM: Gestione dello spazio libero"
date: 2026-03-31 10:11:47 +0200
sintesi: "La Free Space Map (FSM) tiene traccia di dove c'è spazio libero nelle pagine esistenti per nuovi inserimenti. Se la FSM è corrotta o insufficiente, Po..."
tech: db
tags: ['db', 'vacuum & storage']
---
## Esigenza Reale
Evitare la crescita ingiustificata del database in scenari di continuo riciclo di dati (delete seguiti da insert).

## Analisi Tecnica
Problema: Il database chiede nuovo spazio al sistema operativo anche se sono stati appena cancellati milioni di record. Perché: Il Vacuum non sta aggiornando la FSM correttamente. Ho scelto di aumentare la frequenza di analisi per assicurarmi che le mappe di spazio libero siano sempre precise per il motore di inserimento.

## Esempio Implementativo

```sql
/* Analizzo lo spazio libero medio nelle pagine della tabella */ SELECT * FROM pg_freespace('my_table') ORDER BY avail DESC LIMIT 20; /* Se le pagine mostrano avail = 0 nonostante recenti DELETE, la FSM non è aggiornata */ /* Forzo un vacuum per aggiornare la FSM immediatamente */ VACUUM my_table; /* Aumento la memoria dedicata alla manutenzione per gestire FSM di tabelle grandi */ ALTER SYSTEM SET maintenance_work_mem = '512MB'; SELECT pg_reload_conf(); /* Verifico che i nuovi INSERT riutilizzino le pagine libere invece di allocarne di nuove */ SELECT relpages, pg_size_pretty(pg_relation_size('my_table')) AS table_size FROM pg_class WHERE relname = 'my_table'; /* Confronto relpages prima e dopo un ciclo delete+insert+vacuum: deve restare stabile */
```