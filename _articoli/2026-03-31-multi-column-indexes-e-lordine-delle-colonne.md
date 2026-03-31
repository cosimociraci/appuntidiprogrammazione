---
layout: post
title: "Multi-column Indexes e lordine delle colonne"
date: 2026-03-31 19:00:49 
sintesi: "L'ordine delle colonne in un indice composto (B-Tree) è critico. La regola del prefisso stabilisce che un indice su (A, B) può essere usato per ricerche su A e su A+B, ma è quasi inutile per ricerche solo su B. Le colonne con la maggiore selettività "
tech: db
tags: [db, "indexing internals"]
pdf_file: "multi-column-indexes-e-lordine-delle-colonne.pdf"
---

## Esigenza Reale
Progettare un indice efficiente per una tabella di log che viene interrogata spesso per 'applicazione' e 'livello_errore'.

## Analisi Tecnica
Problema: Le query che filtrano solo per la seconda colonna dell'indice non ottengono i benefici prestazionali sperati. Perché: Ho riordinato le colonne basandomi sulla frequenza d'uso. Ho messo 'app_id' per primo perché è presente nel 90% delle query, massimizzando il riutilizzo dello stesso indice.

## Esempio Implementativo

```db
/* Creo l'indice mettendo la colonna più selettiva e più usata nelle WHERE di uguaglianza per prima. Questo indice serve query su (app_id) e query su (app_id + severity), ma non query solo su severity. */ CREATE INDEX idx_logs_app_severity ON logs (app_id, severity); /* Verifico che il Planner usi l'indice per entrambi i pattern di query attesi: */ -- Pattern 1: filtro solo su app_id (usa il prefisso dell'indice) EXPLAIN (ANALYZE, BUFFERS) SELECT id, message, created_at FROM logs WHERE app_id = 7; -- Pattern 2: filtro su entrambe le colonne (usa l'indice completo) EXPLAIN (ANALYZE, BUFFERS) SELECT id, message, created_at FROM logs WHERE app_id = 7 AND severity = 'ERROR'; -- Pattern 3: filtro solo su severity (NON usa l'indice: serve un indice separato) EXPLAIN (ANALYZE, BUFFERS) SELECT id, message, created_at FROM logs WHERE severity = 'ERROR'; /* Per il pattern 3, creo un indice separato o parziale dedicato: */ CREATE INDEX idx_logs_severity_errors ON logs (created_at DESC) WHERE severity = 'ERROR'; /* Estendo l'indice composito con una terza colonna per ottimizzare anche l'ordinamento temporale, frequente nelle query di monitoraggio: */ CREATE INDEX idx_logs_app_severity_time ON logs (app_id, severity, created_at DESC); /* Questa query usa l'indice completo per filtrare e ordinare senza un Sort node aggiuntivo: */ EXPLAIN (ANALYZE) SELECT id, message, created_at FROM logs WHERE app_id = 7 AND severity = 'ERROR' ORDER BY created_at DESC LIMIT 50; /* Verifico quali indici vengono effettivamente usati e quali sono inutilizzati (candidati alla rimozione): */ SELECT indexrelname, idx_scan, idx_tup_read, pg_size_pretty(pg_relation_size(indexrelid)) AS size FROM pg_stat_user_indexes WHERE relname = 'logs' ORDER BY idx_scan ASC; /* Un idx_scan = 0 dopo settimane di produzione è un forte segnale che l'indice è ridondante e va rimosso per alleggerire il carico sugli INSERT. */ /* In Spring Boot con Spring Data JPA, le query generate da metodi come findByAppIdAndSeverity sfruttano automaticamente l'indice composito, mentre findBySeverity non lo farà: è necessario un indice separato su severity o una query nativa con hint. */ @Query("SELECT l FROM Log l WHERE l.appId = :appId AND l.severity = :severity ORDER BY l.createdAt DESC") Page<Log> findByAppIdAndSeverity(@Param("appId") Long appId, @Param("severity") String severity, Pageable pageable);
```
