---
layout: post
title: "Freezing & Wraparound Prevention"
date: 2026-03-31 17:07:58 
sintesi: "Ogni riga ha un Transaction ID (XID). Poiché il contatore è a 32 bit, dopo 2 miliardi di transazioni il database va in "wraparound" (i vecchi dati diventano invisibili). Il "Freezing" è il processo con cui il Vacuum marca le righe vecchie come "conge"
tech: db
tags: ['db', 'vacuum & storage']
---

## Esigenza Reale
Prevenire l'arresto improvviso del database di produzione dovuto al raggiungimento del limite massimo di ID transazione.

## Analisi Tecnica
Problema: Accumulo di ID transazione non congelati che minaccia l'integrità del database a lungo termine. Perché: Regolo autovacuum_freeze_max_age. Ho scelto di abbassare la soglia per far partire il vacuum di "freeze" prima della crisi, distribuendo il carico di manutenzione invece di concentrarlo in un unico evento catastrofico.

## Esempio Implementativo

```db
/* Verifico l'età delle transazioni per ogni database: se supera 1.5 miliardi è urgente */
SELECT
  datname,
  age (datfrozenxid) AS xid_age,
  round(age (datfrozenxid) / 2000000000.0 * 100, 2) AS pct_of_limit
FROM
  pg_database
ORDER BY
  xid_age DESC;

/* Abbasso la soglia di freeze per anticipare il vacuum automatico */
ALTER TABLE high_write_table
SET
  (autovacuum_freeze_max_age = 100000000);

/* Se l'età è già critica (> 150M), eseguo un freeze manuale in orario notturno */
VACUUM FREEZE VERBOSE my_table;

/* Monitoro le tabelle più "anziane" per pianificare i freeze prioritari */
SELECT
  relname,
  age (relfrozenxid) AS table_xid_age
FROM
  pg_class
WHERE
  relkind = 'r'
ORDER BY
  table_xid_age DESC
LIMIT
  10;

/* Imposto un alert operativo: se age(datfrozenxid) supera 500M, invio una notifica */
SELECT
  datname
FROM
  pg_database
WHERE
  age (datfrozenxid) > 500000000;
```
