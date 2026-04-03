---
layout: post
title: "Join Order Control (join_collapse_limit)"
date: 2026-04-03 14:40:28
sintesi: "Quando una query ha molti join, il Planner tenta di rimescolarli per trovare l'ordine pi efficiente. Tuttavia, il numero di combinazioni cresce esponenzialmente. Se superiamo il join_collapse_limit, il Planner smette di cercare l'ordine perfetto e i"
tech: "db"
tags: ["db", "query opt. & planner"]
pdf_file: "join-order-control-joincollapselimit.pdf"
---

## Esigenza Reale
Velocizzare la fase di pianificazione di query enormi prodotte da software di BI che uniscono decine di tabelle.

## Analisi Tecnica
Problema: Tempi di pianificazione (Planning Time) superiori ai tempi di esecuzione a causa della complessità combinatoria dei join. Perché: Ho aumentato il limite di collasso. Ho deciso di dare al Planner più spazio di manovra per query complesse, ma raccomando di scrivere i join nell'ordine di selettività decrescente per aiutare il motore.

## Esempio Implementativo

```db
* Misuro il Planning Time attuale. Se supera il Execution Time, il problema è
* nella fase di pianificazione, non nell'esecuzione. */
 EXPLAIN (ANALYZE, FORMAT TEXT) SELECT o.id, u.name, p.title, c.name AS category
FROM orders o JOIN users u ON o.user_id = u.id JOIN order_items oi ON
oi.order_id = o.id JOIN products p ON oi.product_id = p.id JOIN categories c ON
p.category_id = c.id JOIN promotions pr ON pr.id = o.promotion_id JOIN
warehouses w ON w.id = oi.warehouse_id JOIN shipping_methods sm ON sm.id =
o.shipping_method_id;
* Se il Planning Time è >> Execution Time, abbasso il limite per forzare il
* Planner a rispettare l'ordine scritto nella query. Lo scrivo mettendo le
* tabelle più selettive per prime. */
 SET join_collapse_limit = 1; -- Forza l'ordine esatto dei join come scritto
nella query
* Oppure alzo il limite per dare più libertà al Planner su query con pochi join
* ma complesse: */
 SET join_collapse_limit = 12; 
* Abbino sempre questo parametro a from_collapse_limit, che controlla il
* collasso delle subquery nelle FROM list: */
 SET from_collapse_limit = 8; 
* In Spring Boot con Hibernate, le query generate automaticamente spesso
* producono join in ordine non ottimale. La strategia corretta è usare le query
* native per le operazioni critiche di reporting: */
 @Query(value = """ SELECT o.id, u.name, p.title FROM orders o JOIN users u ON
o.user_id = u.id JOIN order_items oi ON oi.order_id = o.id JOIN products p ON
oi.product_id = p.id WHERE o.created_at >= :from AND u.active = true """,
nativeQuery = true) List<OrderReportRow> findOrderReport(@Param("from")
LocalDateTime from);
* Prima di modificare join_collapse_limit globalmente, verifico il parametro
* attuale e l'impatto sulle query esistenti: */
 SELECT name, setting FROM pg_settings WHERE name IN ('join_collapse_limit',
'from_collapse_limit');
```
