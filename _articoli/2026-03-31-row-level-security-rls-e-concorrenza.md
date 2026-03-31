---
layout: post
title: "Row-Level Security (RLS) e Concorrenza"
date: 2026-03-31 17:04:42 
sintesi: "La sicurezza a livello di riga (RLS) aggiunge un filtro invisibile a ogni query. Sebbene potente, può impattare sulla concorrenza se le policy includono subquery complesse che acquisiscono lock su altre tabelle. Ogni volta che un utente accede a una "
tech: db
tags: ['db', 'concorrenza e locking approfond']
pdf_file: "row-level-security-rls-e-concorrenza.pdf"
---

## Esigenza Reale
Implementare un sistema multi-tenant dove ogni azienda vede solo i propri ordini, garantendo che i lock presi da un tenant non interferiscano con quelli di un altro.

## Analisi Tecnica
Problema: Le policy RLS troppo complesse rallentano l'acquisizione dei lock e possono causare timeout inaspettati. Perché: Uso variabili di sessione personalizzate. Ho scelto di filtrare tramite current_setting('app.tenant_id') perché è un'operazione in memoria che non richiede join aggiuntivi durante il controllo del lock.

## Esempio Implementativo

```db
/* Attivo RLS e definisco policy separate per lettura e scrittura per avere granularità nel controllo degli accessi per tipo di operazione. */ ALTER TABLE orders ENABLE ROW LEVEL SECURITY; CREATE POLICY tenant_isolation_select ON orders FOR SELECT USING (tenant_id = current_setting('app.tenant_id')::int); CREATE POLICY tenant_isolation_modify ON orders FOR ALL USING (tenant_id = current_setting('app.tenant_id')::int) WITH CHECK (tenant_id = current_setting('app.tenant_id')::int); /* Imposto la variabile di sessione all'inizio di ogni connessione, tipicamente in un after-connect hook del connection pool. */ SET app.tenant_id = '42'; /* A livello applicativo (Java + JDBC), la strategia corretta è impostare la variabile immediatamente dopo aver ottenuto la connessione: try (Connection conn = dataSource.getConnection()) { try (Statement stmt = conn.createStatement()) { stmt.execute("SET app.tenant_id = '" + tenantId + "'"); } // Da qui in poi tutte le query sono filtrate automaticamente per tenant } */ /* Verifico che la policy non stia causando heap scan evitabili tramite EXPLAIN. */ EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE order_date > '2026-01-01' FOR UPDATE;
```
