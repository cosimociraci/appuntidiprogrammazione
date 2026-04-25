---
layout: code
title: "Fencing e STONITH in High Availability"
date: 2026-09-23 12:00:00
sintesi: >
  In sistemi HA con failover automatico (es. Patroni), il rischio peggiore è lo "Split Brain", dove due nodi credono di essere entrambi il Master. Il "Fencing" isola il vecchio master mentre "STONITH" (Shoot The Other Node In The Head) ne interrompe fi
tech: "sql"
tags: ["sql", "db"]
pdf_file: "fencing-e-stonith-in-high-availability.pdf"
---

## Esigenza Reale
Evitare che un database "fantasma" continui ad accettare ordini dai clienti mentre il sistema ha già eletto un nuovo master ufficiale.

## Analisi Tecnica
**Problema:** Due istanze Master attive contemporaneamente scrivono dati diversi, rendendo impossibile la riconciliazione futura.

**Perché:** Utilizzo un cluster manager con Distributed Configuration Store (DCS). Ho scelto Patroni perché gestisce nativamente il ciclo di vita del leader tramite chiavi TTL su etcd, garantendo l'univocità del ruolo.

## Esempio Implementativo

```sql
    /* patroni.yml — configurazione TTL e loop */ scope: pg-cluster; ttl: 30;
        loop_wait: 10; maximum_lag_on_failover: 1048576; /* Verifica del leader
        via etcd */ # etcdctl get /service/pg-cluster/leader /* Script STONITH
        chiamato da Patroni prima della promozione */ aws ec2
        revoke-security-group-ingress --group-id sg-xxx --protocol tcp --port
        5432 --source-group sg-app-servers; /* Stato post-failover */ #
        patronictl -c /etc/patroni/patroni.yml list
```
