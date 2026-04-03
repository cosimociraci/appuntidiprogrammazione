---
layout: post
title: "Vacuum Pre-emptive Locking"
date: 2026-04-03 14:40:26
sintesi: "Il Vacuum  un processo di background, ma per finalizzare la pulizia o per troncare una tabella alla fine, ha bisogno di un lock breve ma forte (Access Exclusive). Se la tabella  costantemente sotto query, il Vacuum potrebbe non riuscire mai a finir"
tech: "db"
tags: ["db", "concorrenza e locking approfond"]
pdf_file: "vacuum-pre-emptive-locking.pdf"
---

## Esigenza Reale
Gestire il bloat in tabelle di "sessioni utente" che vengono aggiornate ogni secondo e non lasciano mai spazio al Vacuum.

## Analisi Tecnica
Problema: Il Vacuum viene costantemente interrotto dalle transazioni utente, rendendolo inefficace contro la crescita del database. Perché: Eseguo un VACUUM ANALYZE manuale durante i minimi di traffico. Ho scelto di intervenire proattivamente per evitare che la tabella raddoppi di dimensione inutilmente.

## Esempio Implementativo

```db
* Prima di intervenire, misuro il livello di bloat reale sulla tabella per
* quantificare il problema. */
 SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
pg_size_pretty(pg_relation_size(relid)) AS table_size, n_live_tup, n_dead_tup,
round(100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0), 2) AS dead_pct,
last_vacuum, last_autovacuum FROM pg_stat_user_tables WHERE relname =
'user_sessions' ORDER BY dead_pct DESC;
* Verifico se l'autovacuum è stato interrotto di recente su questa tabella. Un
* contatore 'autovacuum_count' basso nonostante alta attività è un segnale di
* allarme. */
 SELECT relname, autovacuum_count, autoanalyze_count, n_mod_since_analyze FROM
pg_stat_user_tables WHERE relname = 'user_sessions';
* Eseguo un vacuum mirato con parametri aggressivi durante la finestra notturna
* di bassa attività. ANALYZE aggiorna le statistiche per migliorare le scelte
* del Planner sulle query concorrenti. */
 VACUUM (ANALYZE, VERBOSE, PARALLEL 4) user_sessions; 
* Per tabelle con bloat estremo dove VACUUM non è sufficiente, uso pg_repack
* (estensione esterna) che ricostruisce la tabella online senza lock prolungati:
* -- pg_repack -t user_sessions mydb */
 
* Configuro l'autovacuum in modo aggressivo specificamente per questa tabella ad
* alta frequenza di scrittura: */
 ALTER TABLE user_sessions SET ( autovacuum_vacuum_scale_factor = 0.005,
autovacuum_vacuum_cost_delay = '2ms', autovacuum_vacuum_threshold = 100 );
* In Spring Boot, schedulo un job notturno che forza il vacuum durante il minimo
* di traffico: @Scheduled(cron = "0 30 2 * * *")
// Ogni notte alle 02:30 public void performMaintenanceVacuum() 
{ jdbcTemplate.execute("VACUUM (ANALYZE, VERBOSE) user_sessions");
log.info("Vacuum su user_sessions completato"); }
 */
```
