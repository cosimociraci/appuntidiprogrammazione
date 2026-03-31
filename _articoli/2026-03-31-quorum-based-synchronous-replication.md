---
layout: post
title: "Quorum-based Synchronous Replication"
date: 2026-03-31 17:04:42 
sintesi: "Dalla versione 10, PostgreSQL supporta la replica sincrona basata su quorum: la transazione è sicura se N nodi su una lista di M confermano la ricezione. Questo meccanismo evita il "Single Point of Failure" della replica sincrona classica: se uno sta"
tech: db
tags: ['db', 'advanced replication & ha']
pdf_file: "quorum-based-synchronous-replication.pdf"
---

## Esigenza Reale
Garantire la sicurezza dei dati anche se uno dei tre nodi della server farm va offline per un guasto hardware improvviso.

## Analisi Tecnica
Problema: In una replica sincrona 1-a-1, se la replica cade, il Master smette di accettare scritture, causando un downtime totale. Perché: Uso il Quorum Commit. Ho scelto ANY 1 (standby1, standby2) così il Master prosegue finché almeno una delle due repliche è viva e sincronizzata.

## Esempio Implementativo

```db
/* Nel postgresql.conf del Master */ synchronous_standby_names = 'ANY 2 (node_a, node_b, node_c)'; synchronous_commit = on; /* Monitoraggio del quorum in tempo reale */ SELECT application_name, sync_state, pg_wal_lsn_diff(sent_lsn, flush_lsn) AS bytes_not_flushed FROM pg_stat_replication ORDER BY sync_state DESC; /* Test di durabilità */ BEGIN; INSERT INTO ordini (cliente_id, importo, stato) VALUES (42, 1500.00, 'confermato'); COMMIT;
```
