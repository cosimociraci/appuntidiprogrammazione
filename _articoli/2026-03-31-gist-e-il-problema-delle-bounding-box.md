---
layout: post
title: "GiST e il problema delle Bounding Box"
date: 2026-03-31 16:50:23 
sintesi: "L'indice GiST (Generalized Search Tree) è il motore di PostGIS, ma la sua efficienza dipende dalla "qualità" delle Bounding Box (MBR) create. Se le geometrie sono molto sovrapposte o disperse, l'albero GiST diventa inefficiente perché deve scansionar"
tech: db
tags: ['db', 'indexing internals']
pdf_file: "gist-e-il-problema-delle-bounding-box.pdf"
---

## Esigenza Reale
Accelerare le query di geo-fencing che devono identificare in quali aree urbane si trova un veicolo tra milioni di poligoni di quartieri.

## Analisi Tecnica
Problema: Scansione di troppi nodi dell'albero GiST a causa di un'organizzazione spaziale dei dati frammentata. Perché: Ho scelto di ordinare i dati spazialmente prima di indicizzarli. Questo processo, chiamato "Clustering", massimizza la selettività di ogni ramo dell'indice GiST.

## Esempio Implementativo

```db
/* Creo prima l'indice GiST, poi eseguo il CLUSTER per riordinare fisicamente la tabella seguendo l'ordine spaziale dell'indice. Le zone geograficamente vicine vengono così scritte in pagine disco adiacenti. */ CREATE INDEX idx_geo_polygons ON city_zones USING GIST (geom); CLUSTER city_zones USING idx_geo_polygons; ANALYZE city_zones; /* Verifico il miglioramento con una query di geo-fencing tipica. Cerco il quartiere che contiene una coordinata GPS specifica. */ EXPLAIN (ANALYZE, BUFFERS) SELECT zone_name, municipality FROM city_zones WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(10.2035, 45.5416), 4326)); /* Confronto "Buffers: shared read" prima e dopo il CLUSTER: se le bounding box si sovrappongono meno, il Planner percorre meno rami e legge meno pagine disco. */ /* Per query k-Nearest Neighbor (trova i 5 quartieri più vicini a un punto), l'indice GiST usa l'operatore <->. Dopo il CLUSTER, le performance migliorano sensibilmente: */ SELECT zone_name, geom <-> ST_SetSRID(ST_MakePoint(10.2035, 45.5416), 4326) AS dist FROM city_zones ORDER BY dist LIMIT 5; /* Il CLUSTER non mantiene l'ordine per i nuovi inserimenti. Schedulo una manutenzione periodica notturna: */ -- CLUSTER city_zones USING idx_geo_polygons; -- ANALYZE city_zones; /* Per evitare il lock esclusivo del CLUSTER su tabelle molto trafficate, uso pg_repack con ordinamento spaziale come alternativa non bloccante: */ -- pg_repack -t city_zones --order-by "ST_GeoHash(ST_Centroid(geom), 10)" mydb /* In Spring Boot con Spring Data JPA + Hibernate Spatial, la query k-NN si traduce in: */ @Query(value = """ SELECT zone_name FROM city_zones ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) LIMIT :k """, nativeQuery = true) List<String> findNearestZones(@Param("lon") double lon, @Param("lat") double lat, @Param("k") int k);
```
