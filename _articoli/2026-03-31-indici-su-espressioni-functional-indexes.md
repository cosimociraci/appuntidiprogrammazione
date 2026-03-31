---
layout: post
title: "Indici su Espressioni (Functional Indexes)"
date: 2026-03-31 16:50:23 
sintesi: "Molte query falliscono l'uso degli indici perché applicano funzioni alle colonne (es. WHERE lower(name) = 'rossi'). Un indice standard su name non serve in questo caso. La soluzione è un indice su espressione, dove il risultato della funzione viene p"
tech: db
tags: ['db', 'indexing internals']
pdf_file: "indici-su-espressioni-functional-indexes.pdf"
---

## Esigenza Reale
Ottimizzare la ricerca per data (escludendo l'orario) su una colonna di tipo TIMESTAMP senza dover castare ogni riga durante la query.

## Analisi Tecnica
Problema: L'indice non viene usato perché la clausola WHERE trasforma il dato della colonna, rendendolo non confrontabile con i valori grezzi dell'indice. Perché: Ho creato un indice funzionale. Ho scelto di pre-calcolare il cast a DATE nell'indice per rendere le ricerche cronologiche veloci quanto un lookup di intero.

## Esempio Implementativo

```db
/* Creo l'indice funzionale sul cast a DATE. Le parentesi attorno all'espressione sono obbligatorie per distinguerla da un nome di colonna. */ CREATE INDEX idx_orders_day ON orders ((created_at::DATE)); /* Verifico che il Planner usi l'indice. La query deve usare esattamente la stessa espressione presente nell'indice: */ EXPLAIN (ANALYZE, BUFFERS) SELECT id, customer_id, total_amount FROM orders WHERE created_at::DATE = '2026-03-15'; /* Creo un indice funzionale per ricerche case-insensitive sul cognome. Uso lower() che è IMMUTABLE: */ CREATE INDEX idx_customers_lastname_lower ON customers (lower(last_name)); /* La query deve usare la stessa funzione nella WHERE per sfruttare l'indice: */ SELECT id, first_name, last_name FROM customers WHERE lower(last_name) = 'rossi'; /* Creo un indice funzionale su un'espressione più complessa: estraggo l'anno e il mese da un timestamp per raggruppamenti mensili frequenti nei report: */ CREATE INDEX idx_orders_year_month ON orders (date_trunc('month', created_at)); EXPLAIN (ANALYZE) SELECT date_trunc('month', created_at) AS month, sum(total_amount) FROM orders WHERE date_trunc('month', created_at) = '2026-03-01' GROUP BY 1; /* Verifico che tutte le funzioni usate negli indici siano effettivamente IMMUTABLE, altrimenti Postgres rifiuta la creazione dell'indice: */ SELECT proname, provolatile FROM pg_proc WHERE proname IN ('lower', 'date_trunc', 'to_tsvector') AND pronamespace = 'pg_catalog'::regnamespace; /* In Spring Boot con Spring Data JPA, per sfruttare l'indice funzionale la query nativa deve replicare esattamente l'espressione: */ @Query(value = "SELECT * FROM orders WHERE created_at::DATE = :targetDate", nativeQuery = true) List<Order> findByDate(@Param("targetDate") LocalDate targetDate); /* Con JPQL standard non è possibile replicare espressioni SQL custom: in questi casi la query nativa è l'unica strada per garantire l'uso dell'indice funzionale. */
```
