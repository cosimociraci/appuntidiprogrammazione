---
layout: post
title: "Materialized CTE vs Inline"
date: 2026-03-31 17:07:42 
sintesi: "Prima di PostgreSQL 12, le Common Table Expressions (CTE) erano "optimization fences": venivano sempre calcolate e caricate in memoria (materializzate) prima del resto della query. Oggi il Planner le "inlinea" per ottimizzarle. Tuttavia, a volte è ne"
tech: db
tags: ['db', 'query opt. & planner']
---

## Esigenza Reale
Risolvere query con molteplici join dove il Planner tenta di applicare filtri troppo tardi, causando scansioni enormi su tabelle intermedie.

## Analisi Tecnica
Problema: Il Planner "sposta" i predicati dentro la CTE in modo inefficiente, causando ricalcoli continui di funzioni volatili. Perché: Uso AS MATERIALIZED. Ho scelto questa strada per creare un confine netto: il database deve risolvere prima la CTE e poi usare il risultato statico, evitando piani di esecuzione instabili.

## Esempio Implementativo

```db
/* Confronto il comportamento con e senza MATERIALIZED per capire l'impatto sul piano di esecuzione. */ -- Versione inline (default Postgres 12+): il Planner può spostare i predicati dentro la CTE. EXPLAIN (ANALYZE, BUFFERS) WITH monthly_stats AS ( SELECT user_id, avg(amount) AS avg_spend FROM orders GROUP BY user_id ) SELECT u.name, s.avg_spend FROM users u JOIN monthly_stats s ON u.id = s.user_id WHERE u.active = true; /* Versione materializzata: il Planner calcola prima tutta la CTE e poi esegue il join sul risultato "congelato". Utile quando la CTE contiene funzioni VOLATILE o aggregati costosi che non devono essere replicati per ogni riga del join. */ EXPLAIN (ANALYZE, BUFFERS) WITH monthly_stats AS MATERIALIZED ( SELECT user_id, avg(amount) AS avg_spend, count(*) AS order_count, max(created_at) AS last_order_date FROM orders WHERE created_at >= date_trunc('month', now() - interval '1 month') GROUP BY user_id ) SELECT u.name, u.email, s.avg_spend, s.order_count FROM users u JOIN monthly_stats s ON u.id = s.user_id WHERE u.active = true AND s.avg_spend > 100 ORDER BY s.avg_spend DESC; /* Uso NOT MATERIALIZED per forzare l'inlining anche su Postgres pre-12 o in contesti dove so che il Planner si comporta meglio con la CTE espansa: */ WITH filtered_users AS NOT MATERIALIZED ( SELECT id FROM users WHERE country = 'IT' ) SELECT o.* FROM orders o WHERE o.user_id IN (SELECT id FROM filtered_users);
```
