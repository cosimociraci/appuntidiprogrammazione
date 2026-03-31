---
layout: post
title: "Covering Indexes (Clausola INCLUDE)"
date: 2026-03-31 17:04:42 
sintesi: "Introdotta in Postgres 11, la clausola INCLUDE permette di creare indici "coprenti". Questo permette di aggiungere colonne extra ai nodi foglia dell'indice che non fanno parte della chiave di ricerca. Il vantaggio tecnico è rilevante: permette gli "I"
tech: db
tags: ['db', 'indexing internals']
pdf_file: "covering-indexes-clausola-include.pdf"
---

## Esigenza Reale
Velocizzare una query frequente che cerca l'email di un utente partendo dal suo ID, evitando il "Table Access" dopo aver trovato l'ID nell'indice.

## Analisi Tecnica
Problema: Anche se l'ID è indicizzato, il database deve comunque leggere la tabella per recuperare la colonna 'email'. Perché: Uso INCLUDE. Ho scelto di "portare" l'email dentro l'indice dell'ID per permettere un Index-Only Scan, dimezzando di fatto il numero di blocchi letti dal disco.

## Esempio Implementativo

```db
/* Creo l'indice coprente. user_id è la chiave di ricerca; email, username e status sono payload disponibili per la SELECT senza toccare la heap. */ CREATE INDEX idx_users_id_covering ON users (user_id) INCLUDE (email, username, status); /* Verifico che il Planner usi un Index-Only Scan e non un Index Scan + Heap Fetch: */ EXPLAIN (ANALYZE, BUFFERS) SELECT email, username, status FROM users WHERE user_id = 550; /* Nell'output cerco: Index Only Scan using idx_users_id_covering on users Heap Fetches: 0 -- Se è 0, la Visibility Map è aggiornata e l'indice lavora al 100% */ /* Se Heap Fetches > 0, forzo un VACUUM per aggiornare la Visibility Map: */ VACUUM (ANALYZE) users; /* Applico la stessa tecnica a una query di reportistica frequente che recupera dati di riepilogo degli ordini per un cliente: */ CREATE INDEX idx_orders_customer_covering ON orders (customer_id, created_at DESC) INCLUDE (total_amount, status, shipping_address_id); /* La query seguente non toccherà mai la tabella orders: */ EXPLAIN (ANALYZE, BUFFERS) SELECT created_at, total_amount, status FROM orders WHERE customer_id = 1042 ORDER BY created_at DESC LIMIT 20; /* Confronto la dimensione dell'indice coprente con quella di un indice semplice per valutare il tradeoff storage vs performance: */ SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid)) AS size FROM pg_stat_user_indexes WHERE relname = 'orders'; /* Regola pratica: includo in INCLUDE solo le colonne selezionate frequentemente, non tutte. Le colonne INCLUDE non possono essere usate come chiave di ricerca o di ordinamento, quindi non appesantiscono la struttura ad albero, solo i nodi foglia. */ /* In Spring Boot, la query JPA che beneficia dell'indice coprente deve selezionare esattamente le colonne presenti nell'indice. Uso una Projection per evitare di caricare l'intera entity: */ public interface OrderSummary { LocalDateTime getCreatedAt(); BigDecimal getTotalAmount(); String getStatus(); } @Query("SELECT o.createdAt as createdAt, o.totalAmount as totalAmount, o.status as status FROM Order o WHERE o.customerId = :customerId ORDER BY o.createdAt DESC") List<OrderSummary> findOrderSummaries(@Param("customerId") Long customerId, Pageable pageable);
```
