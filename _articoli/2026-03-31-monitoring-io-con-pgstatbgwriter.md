---
layout: post
title: "Monitoring I/O con pg_stat_bgwriter"
date: 2026-03-31 17:04:42 
sintesi: "Il Background Writer ha il compito di scrivere le pagine sporche dalla memoria al disco in modo graduale, evitando picchi durante i Checkpoint. Se il numero di buffers_backend è alto, significa che le query degli utenti sono costrette a scrivere i da"
tech: db
tags: ['db', 'vacuum & storage']
pdf_file: "monitoring-io-con-pgstatbgwriter.pdf"
---

## Esigenza Reale
Rendere fluide le transazioni di inserimento massivo evitando che i processi utente rimangano bloccati dall'attesa dell'I/O disco.

## Analisi Tecnica
Problema: Picchi di latenza improvvisi durante le scritture pesanti, dovuti a un inefficiente scaricamento della cache sul disco. Perché: Analizzo le statistiche del bgwriter. Ho scelto di calibrare i parametri di scrittura in background per "spalmare" l'I/O nel tempo, garantendo che ci sia sempre spazio libero nei buffer per le nuove transazioni.

## Esempio Implementativo

```db
/* Analizzo le statistiche del bgwriter per capire dove si trova il collo di bottiglia. Il reset delle statistiche all'inizio mi dà una baseline pulita per il confronto. */ SELECT pg_stat_reset_shared('bgwriter'); -- Resetto le statistiche (solo in sessione di analisi) /* Dopo un periodo di carico rappresentativo, leggo le metriche: */ SELECT buffers_checkpoint, -- Pagine scritte durante i checkpoint (normale) buffers_clean, -- Pagine scritte dal bgwriter in background (ottimale) buffers_backend, -- Pagine scritte direttamente dai processi utente (problema!) buffers_backend_fsync, -- fsync eseguiti dai backend (critico: indica saturazione I/O) maxwritten_clean, -- Volte che il bgwriter ha raggiunto il limite e si è fermato checkpoint_write_time, checkpoint_sync_time, -- Tempo speso nei checkpoint: se alto, i checkpoint sono troppo pesanti now() - stats_reset AS stats_age FROM pg_stat_bgwriter; /* Interpretazione: buffers_backend alto -> il bgwriter è troppo lento, aumentare bgwriter_lru_maxpages maxwritten_clean alto -> il bgwriter raggiunge il limite e si ferma, aumentare bgwriter_lru_maxpages checkpoint_sync_time alto -> i checkpoint sono bloccanti, aumentare max_wal_size per diradarli */ /* Calibro i parametri nel postgresql.conf per rendere il bgwriter più aggressivo: bgwriter_delay = 50ms -- Default 200ms: sveglia il bgwriter più spesso bgwriter_lru_maxpages = 200 -- Default 100: scrive più pagine per ciclo bgwriter_lru_multiplier = 4.0 -- Default 2.0: più buffer preallocati per le richieste future */ /* Monitoro anche i checkpoint per capire se sono troppo frequenti: */ SELECT checkpoints_timed, -- Checkpoint pianificati (normale) checkpoints_req, -- Checkpoint forzati dal volume di WAL (problema se alto) checkpoint_write_time / nullif(checkpoints_timed + checkpoints_req, 0) AS avg_write_ms, checkpoint_sync_time / nullif(checkpoints_timed + checkpoints_req, 0) AS avg_sync_ms FROM pg_stat_bgwriter; /* Se checkpoints_req è alto rispetto a checkpoints_timed, aumento max_wal_size per diradare i checkpoint forzati: max_wal_size = 4GB -- Default 1GB: consente WAL più grandi prima del checkpoint checkpoint_completion_target = 0.9 -- Spalma la scrittura su 90% dell'intervallo tra checkpoint */ /* Verifico il tasso di hit della shared_buffers per capire se la cache è sufficiente: */ SELECT sum(heap_blks_hit) AS cache_hits, sum(heap_blks_read) AS disk_reads, round(100.0 * sum(heap_blks_hit) / nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0), 2) AS cache_hit_pct FROM pg_statio_user_tables; /* Un cache_hit_pct < 95% su workload OLTP indica che shared_buffers è troppo piccola: il valore raccomandato è il 25% della RAM disponibile. */ /* In Spring Boot, monitoro buffers_backend tramite un Micrometer gauge esposto su Actuator per rilevare in tempo reale i picchi di I/O diretto dai backend: */ @Bean public MeterBinder bgwriterMetrics(JdbcTemplate jdbcTemplate) { return registry -> { Gauge.builder("postgres.bgwriter.buffers_backend", jdbcTemplate, jt -> { Map<String, Object> row = jt.queryForMap( "SELECT buffers_backend FROM pg_stat_bgwriter"); return ((Number) row.get("buffers_backend")).doubleValue(); }).register(registry); }; }
```
