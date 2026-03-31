---
layout: post
title: "JIT Compilation Tuning"
date: 2026-03-31 16:39:58 
tech: db
tags: ['db', 'query opt. & planner']
pdf_file: "jit-compilation-tuning.pdf"
---

## Esigenza Reale
Eliminare micro-latenze fastidiose su query di lookup di chiavi primarie che inspiegabilmente impiegano più tempo del previsto.

## Analisi Tecnica
Problema: L'overhead di compilazione JIT aggiunge 50-100ms a query che dovrebbero girare in 1ms. Perché: Disabilito JIT a livello di sessione o transazione. Ho scelto questa configurazione perché le mie query sono semplici e il guadagno della compilazione non copre il costo iniziale della stessa.

## Esempio Implementativo

```db
/* Verifico se JIT è attivo e se sta intervenendo sulla query problematica. Nell'output di EXPLAIN ANALYZE cerco la sezione "JIT" con i tempi di "Generation" e "Inlining". */ SET jit = on; EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM users WHERE id = 45678; /* Se vedo qualcosa come: JIT: Functions: 3 Options: Inlining true, Optimization true, Expressions true Generation Time: 2.451 ms Emission Time: 18.305 ms con un'esecuzione totale di 1ms, JIT sta peggiorando la situazione. Lo disabilito: */ SET jit = off; EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM users WHERE id = 45678; /* Il tempo totale scende perché saltiamo la fase di compilazione LLVM. Per non disabilitarlo globalmente, alzo le soglie di costo minimo oltre le quali JIT interviene. Il default è 100000, lo porto a 500000 per escluderlo dalle query leggere: */ SET jit_above_cost = 500000; SET jit_optimize_above_cost = 1000000; SET jit_inline_above_cost = 750000; /* Per la configurazione permanente nel postgresql.conf: jit = on -- Lo tengo abilitato globalmente jit_above_cost = 500000 -- Interviene solo su query analitiche costose */ /* In Spring Boot, posso disabilitare JIT per il DataSource OLTP e tenerlo abilitato per un DataSource dedicato ai report: @Bean public DataSource oltpDataSource() { HikariConfig config = new HikariConfig(); config.setConnectionInitSql("SET jit = off"); return new HikariDataSource(config); } */
```
