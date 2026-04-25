---
layout: code
title: "Extended Statistics (CREATE STATISTICS)"
date: 2026-11-25 12:00:00
sintesi: >
  Il Planner assume solitamente che le colonne siano indipendenti tra loro. Se interroghiamo una tabella filtrando per "Marca" e "Modello", Postgres moltiplica le selettività singole, spesso sottostimando il numero di righe risultanti. CREATE STATISTIC
tech: "sql"
tags: ["sql", "db", "analyze"]
pdf_file: "extended-statistics-create-statistics.pdf"
---

## Esigenza Reale
Ottimizzare le ricerche in un catalogo e-commerce dove i filtri (es. Colore e Taglia) sono fortemente correlati e causano stime di righe errate.

## Analisi Tecnica
**Problema:** Stime di cardinalità errate portano alla scelta di join inefficienti (Nested Loop invece di Hash Join).

**Perché:** Ho creato statistiche di dipendenza. In questo modo il database "impara" che certi valori viaggiano insieme, permettendogli di calcolare la selettività reale del filtro combinato.

## Esempio Implementativo

```sql
    /* Creo statistiche di dipendenza per la coppia city/zip_code che sono
        logicamente correlate: conoscere lo zip determina quasi univocamente la
        city. */ CREATE STATISTICS city_zip_dep (dependencies) ON city, zip_code
        FROM addresses; /* Creo anche statistiche di tipo MCV (Most Common
        Values) multidimensionale per la coppia brand/model nel catalogo
        prodotti: un Planner senza queste statistiche potrebbe stimare "Ferrari
        Panda" come un insieme di righe realistico. */ CREATE STATISTICS
        product_brand_model (dependencies, mcv) ON brand, model FROM products;
        /* Aggiorno le statistiche per rendere effettive le nuove definizioni.
        */ ANALYZE addresses; ANALYZE products; /* Verifico che le statistiche
        siano state create correttamente e che Postgres le stia effettivamente
        usando: */ SELECT stxname, stxkeys, stxkind, stxdependencies FROM
        pg_statistic_ext JOIN pg_statistic_ext_data ON pg_statistic_ext.oid =
        pg_statistic_ext_data.stxoid WHERE stxname IN ('city_zip_dep',
        'product_brand_model'); /* Confronto la stima del Planner prima e dopo
        ANALYZE. Il campo "rows" nell'EXPLAIN dovrebbe avvicinarsi al valore
        reale "actual rows". */ EXPLAIN (ANALYZE) SELECT * FROM products WHERE
        brand = 'Levi''s' AND model = '501'; /* Se la stima era 5 righe e quelle
        reali erano 5000, dopo CREATE STATISTICS la stima dovrebbe essere molto
        più accurata, portando il Planner a scegliere un Hash Join al posto di
        un Nested Loop. */
```
