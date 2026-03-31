---
layout: post
title: "Conflict Detection in Logical Replication"
date: 2026-03-31 17:07:53 
sintesi: "A differenza della replica fisica, quella logica può incontrare conflitti (es. un inserimento sulla replica di una riga con una chiave primaria già esistente). Quando ciò accade, la replica si blocca e smette di applicare le modifiche, creando un lag"
tech: db
tags: ['db', 'advanced replication & ha']
---

## Esigenza Reale
Gestire flussi di dati bidirezionali tra filiali regionali dove è possibile che vengano generati ID duplicati se non coordinati.

## Analisi Tecnica
Problema: Interruzione del flusso di replica dovuto a violazioni di vincoli di integrità sul nodo di destinazione. Perché: Implemento il monitoraggio del lag e logica di skipping. Ho scelto di non permettere scritture locali sulla replica per minimizzare i conflitti strutturali alla radice.

## Esempio Implementativo

```db
/* Verifico il lag della replica e lo stato attuale della subscription per rilevare se si è bloccata. */
SELECT
  subname,
  received_lsn,
  latest_end_lsn,
  pg_wal_lsn_diff(latest_end_lsn, received_lsn) AS lag_bytes
FROM
  pg_stat_subscription;

/* Se la replica è bloccata, trovo l'LSN della transazione problematica nei log di PostgreSQL. Il messaggio tipico è: ERROR: duplicate key value violates unique constraint "orders_pkey" DETAIL: Key (id)=(42) already exists. CONTEXT: processing remote data for replication origin "pg_16390" */ /* Identifico l'LSN da saltare dal log di errore e lo passo al comando SKIP: */
ALTER SUBSCRIPTION my_sub SKIP (lsn = '0/12345678');

/* Prevengo i conflitti alla radice usando sequenze non sovrapposte tra le filiali. Ogni filiale ha un range di ID dedicato: */ -- Filiale Roma: ALTER SEQUENCE orders_id_seq START WITH 1000000 INCREMENT BY 10; -- Filiale Milano: ALTER SEQUENCE orders_id_seq START WITH 2000000 INCREMENT BY 10; /* In alternativa, uso UUID come chiave primaria per eliminare completamente il rischio di collisione tra nodi: */ ALTER TABLE orders ADD COLUMN uuid_id UUID DEFAULT gen_random_uuid(); /* Imposto la replica verso il data warehouse in sola lettura per bloccare scritture accidentali che causerebbero conflitti: */ REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM app_user; /* Monitoro il numero di conflitti accumulati per subscription: */ SELECT subname, conflict_reason, count FROM pg_stat_subscription_stats; /* In Spring Boot, il servizio che legge dalla replica deve gestire dati potenzialmente obsoleti e includere un fallback sul primario per i dati critici: @Transactional(readOnly = true) public Order findOrder(Long id) { try { return replicaOrderRepository.findById(id) .orElseThrow(() -> new OrderNotFoundException(id)); } catch (DataAccessException e) { log.warn("Fallback al primario per ordine {}", id); return primaryOrderRepository.findById(id) .orElseThrow(() -> new OrderNotFoundException(id)); } } */
```
