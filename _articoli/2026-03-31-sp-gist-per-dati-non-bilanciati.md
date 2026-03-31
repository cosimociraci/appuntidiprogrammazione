---
layout: post
title: "SP-GiST per Dati Non Bilanciati"
date: 2026-03-31 17:04:42 
sintesi: "Lo Space-Partitioned GiST (SP-GiST) è un'evoluzione per strutture dati non bilanciate come alberi radi (quadtree, k-d trees). A differenza di GiST, che divide il set di dati in sotto-insiemi potenzialmente sovrapposti, SP-GiST divide lo spazio in reg"
tech: db
tags: ['db', 'indexing internals']
pdf_file: "sp-gist-per-dati-non-bilanciati.pdf"
---

## Esigenza Reale
Ottimizzare un database di indirizzi stradali con milioni di coordinate GPS puntuali concentrate in aree metropolitane dense.

## Analisi Tecnica
Problema: L'indice GiST standard soffre di troppi overlap in zone con altissima densità di punti (es. centri città), rallentando i lookup. Perché: Uso SP-GiST. Ho scelto questo metodo perché la partizione dello spazio senza sovrapposizioni elimina l'ambiguità durante la discesa dell'albero, migliorando le performance di ricerca puntuale.

## Esempio Implementativo

```db
/* Creo l'indice SP-GiST sulla colonna di tipo point. Per dati puntuali puri, SP-GiST è spesso più veloce e più compatto di GiST perché non gestisce geometrie sovrapposte. */ CREATE INDEX idx_addresses_spgist ON addresses USING SPGIST (location); /* Confronto le performance con un indice GiST equivalente sulla stessa tabella per misurare il guadagno reale: */ CREATE INDEX idx_addresses_gist ON addresses USING GIST (location); /* Eseguo la stessa query k-NN con entrambi gli indici e confronto i tempi: */ EXPLAIN (ANALYZE, BUFFERS) SELECT street, city, location <-> point(10.2035, 45.5416) AS dist FROM addresses ORDER BY dist LIMIT 10; /* Forzo il Planner a usare uno specifico indice disabilitando l'altro per il confronto: */ SET enable_indexscan = off; -- Disabilito temporaneamente per forzare l'uso di SP-GiST vs GiST /* Verifico la dimensione dei due indici per quantificare il risparmio di storage: */ SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid)) AS size FROM pg_stat_user_indexes WHERE relname = 'addresses' AND indexrelname IN ('idx_addresses_spgist', 'idx_addresses_gist'); /* SP-GiST supporta anche ricerche per prefisso su stringhe (es. per un sistema di autocompletamento): */ CREATE INDEX idx_streets_prefix ON addresses USING SPGIST (street text_ops); SELECT street FROM addresses WHERE street ^@ 'Via Gari'; -- Operatore prefisso /* Per coordinate geografiche in formato PostGIS (geometry point), SP-GiST è supportato dal tipo geography solo in alcune versioni. Verifico la compatibilità: */ SELECT opfname, opcname FROM pg_opclass WHERE opcmethod = (SELECT oid FROM pg_am WHERE amname = 'spgist') ORDER BY opfname; /* In Spring Boot con Hibernate Spatial, la query k-NN su SP-GiST si scrive come query nativa. Hibernate non genera automaticamente l'operatore <-> necessario per sfruttare l'indice SP-GiST: */ @Query(value = """ SELECT street, city FROM addresses ORDER BY location <-> point(:lon, :lat) LIMIT :k """, nativeQuery = true) List<AddressRow> findNearest(@Param("lon") double lon, @Param("lat") double lat, @Param("k") int k);
```
