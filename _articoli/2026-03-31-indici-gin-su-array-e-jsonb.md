---
layout: post
title: "Indici GIN su Array e JSONB"
date: 2026-03-31 17:07:51 
sintesi: "PostgreSQL eccelle nel gestire dati non strutturati grazie agli indici GIN applicati ad array o oggetti JSONB. Questi indici permettono di interrogare "l'interno" del dato: trovare tutti i documenti che contengono un certo tag o una specifica chiave/"
tech: db
tags: ['db', 'indexing internals']
---

## Esigenza Reale
Implementare un sistema di ricerca filtri per un e-commerce dove ogni prodotto ha attributi variabili salvati in un campo JSONB.

## Analisi Tecnica
Problema: Le query che cercano chiavi nidificate dentro il JSONB eseguono un Sequential Scan perché il database non sa come "entrare" nell'oggetto. Perché: Uso un indice GIN con jsonb_path_ops. Ho scelto questa opzione perché mi interessano solo le query di contenimento (@>), ottenendo un indice più snello e performante rispetto a quello standard.

## Esempio Implementativo

```db
/* Creo l'indice GIN con jsonb_path_ops per query di contenimento. È più piccolo di jsonb_ops perché non indicizza le chiavi isolate, solo i path completi. */
CREATE INDEX idx_products_attrs_path ON products USING GIN (attributes jsonb_path_ops);

/* Verifico che il Planner usi l'indice per la query di contenimento: */
EXPLAIN (
  ANALYZE,
  BUFFERS
)
SELECT
  id,
  name,
  price
FROM
  products
WHERE
  attributes @> '{"color": "red", "size": "XL"}';

/* Per confronto, creo anche l'indice con jsonb_ops (default) che supporta operatori aggiuntivi come ?, ?|, ?& (esistenza chiave): */
CREATE INDEX idx_products_attrs_ops ON products USING GIN (attributes);

-- Con jsonb_ops posso fare query su esistenza di chiave (non supportata da jsonb_path_ops): SELECT id, name FROM products WHERE attributes ? 'discount_code'; SELECT id, name FROM products WHERE attributes ?| ARRAY['color', 'size']; /* Confronto la dimensione dei due indici per quantificare il risparmio: */ SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid)) AS size FROM pg_stat_user_indexes WHERE relname = 'products' AND indexrelname IN ('idx_products_attrs_path', 'idx_products_attrs_ops'); /* Applico lo stesso concetto agli array. Per una tabella di articoli con un campo tags text[], creo un indice GIN che permette ricerche di contenimento e sovrapposizione: */ CREATE INDEX idx_articles_tags ON articles USING GIN (tags); -- Trova articoli che contengono TUTTI i tag specificati: SELECT id, title FROM articles WHERE tags @> ARRAY['postgresql', 'performance']; -- Trova articoli che contengono ALMENO UNO dei tag specificati: SELECT id, title FROM articles WHERE tags && ARRAY['postgresql', 'indexing']; /* Verifico le performance prima e dopo la creazione dell'indice GIN su array: */ EXPLAIN (ANALYZE, BUFFERS) SELECT id, title FROM articles WHERE tags @> ARRAY['postgresql']; /* In Spring Boot, le query su JSONB con indice GIN richiedono query native. Con Spring Data JPA non è possibile esprimere l'operatore @> in JPQL: */ @Query(value = "SELECT * FROM products WHERE attributes @> :filter::jsonb", nativeQuery = true) List<Product> findByAttributes(@Param("filter") String jsonFilter); /* Lato Java, costruisco il filtro JSON come stringa: */ String filter = objectMapper.writeValueAsString(Map.of("color", "red", "size", "XL")); List<Product> results = productRepository.findByAttributes(filter);
```
