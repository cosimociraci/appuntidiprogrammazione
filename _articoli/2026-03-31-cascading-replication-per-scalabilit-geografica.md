---
layout: post
title: "Cascading Replication per Scalabilità Geografica"
date: 2026-03-31 16:50:23 
sintesi: "In architetture distribuite globalmente, avere 100 repliche collegate a un unico Master saturerebbe la sua banda di rete. La "Cascading Replication" permette a una replica di comportarsi a sua volta come un publisher per altre repliche "nipoti". Ques"
tech: db
tags: ['db', 'advanced replication & ha']
pdf_file: "cascading-replication-per-scalabilit-geografica.pdf"
---

## Esigenza Reale
Distribuire i dati di un'app globale in Europa, USA e Asia senza sovraccaricare il database centrale situato in Italia.

## Analisi Tecnica
Problema: Saturazione delle risorse di rete e CPU del nodo Master a causa del numero eccessivo di repliche dirette. Perché: Implemento la replica a cascata. Ho scelto questo design per far sì che solo un nodo per regione geografica parli con il Master, distribuendo poi i dati localmente agli altri nodi della regione.

## Esempio Implementativo

```db
/* Sulla replica intermedia (Hub regionale) */ primary_conninfo = 'host=master_italy port=5432 user=rep_user'; wal_level = replica; hot_standby = on; max_wal_senders = 5; /* Le repliche locali si collegano a questo hub, non al master originale */ primary_conninfo = 'host=hub_usa port=5432 user=rep_user'; /* Verifica della cascata dal Master */ SELECT application_name, client_addr, pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag_bytes FROM pg_stat_replication ORDER BY application_name;
```
