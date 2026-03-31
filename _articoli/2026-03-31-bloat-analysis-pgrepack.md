---
layout: post
title: "Bloat Analysis & pg_repack"
date: 2026-03-31 17:02:46 
sintesi: "Il Vacuum recupera lo spazio all'interno del file, ma non lo restituisce al sistema operativo. Una tabella con molto "bloat" è come una spugna con troppi buchi: occupa molto spazio ma contiene pochi dati utili. Se il bloat è eccessivo (es. >30%), le "
tech: db
tags: ['db', 'vacuum & storage']
pdf_file: "bloat-analysis-pgrepack.pdf"
---

## Esigenza Reale
Recuperare 200GB di spazio disco "fantasma" su una tabella che ha subito una cancellazione massiva di dati storici.

## Analisi Tecnica
Problema: Tabella enorme che occupa molto più spazio della somma reale dei record, rallentando le query sequenziali. Perché: Identifico il bloat tramite query su pg_stat_user_tables. Ho scelto di usare un approccio di ricostruzione online per minimizzare il downtime pur riorganizzando fisicamente i dati sul disco.

## Esempio Implementativo

```db
/* Stimo il bloat confrontando dimensione reale e dimensione attesa */ SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS total_size, n_live_tup, n_dead_tup, round(n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0) * 100, 2) AS bloat_pct FROM pg_stat_user_tables WHERE n_dead_tup > 10000 ORDER BY bloat_pct DESC; /* Se bloat_pct > 30%, procedo con pg_repack invece di VACUUM FULL */ /* Installo pg_repack come estensione */ CREATE EXTENSION pg_repack; /* Eseguo la ricostruzione online: nessun lock esclusivo sulla tabella */ pg_repack -h localhost -d mydb -t bloated_table /* Verifico la riduzione di spazio dopo il repack */ SELECT pg_size_pretty(pg_total_relation_size('bloated_table')) AS size_after; /* Ricostruisco anche gli indici della tabella in un unico passaggio */ pg_repack -h localhost -d mydb -t bloated_table --only-indexes
```
