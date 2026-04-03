---
layout: post
title: "Visibility Map e Index Scans"
date: 2026-04-03 14:45:26
sintesi: >
  La Visibility Map (VM) è un file che indica a Postgres quali blocchi contengono solo tuple visibili a tutti. Senza una VM aggiornata, gli 'Index-Only Scans' non funzionano: il DB deve comunque leggere la tabella per verificare la visibilità. Il Vacuu
tech: "db"
tags: ["db", "vacuum & storage"]
pdf_file: "visibility-map-e-index-scans.pdf"
---

## Esigenza Reale
Ottimizzare il conteggio di righe o la ricerca di colonne indicizzate su tabelle massicce, garantendo che il database non legga mai la tabella heap.

## Analisi Tecnica
Problema: Query che dovrebbero usare solo l'indice risultano lente perché devono accedere continuamente ai dati della tabella per confermare la visibilità MVCC. Perché: Monitoro lo stato della Visibility Map. Ho scelto di forzare il vacuum sulle tabelle critiche per "congelare" le pagine e abilitare l'ottimizzazione Index-Only Scan in modo costante.

## Esempio Implementativo

```sql
* Controllo la percentuale di pagine visibili: se è bassa, l'Index-Only Scan non
* sarà efficace */
 SELECT relname, relpages, relallvisible, round((relallvisible::float /
NULLIF(relpages::float, 0)) * 100, 2) AS visibility_pct FROM pg_class WHERE
relname = 'orders';
/* Se visibility_pct < 90, forzo un vacuum per aggiornare la VM */
 VACUUM (ANALYZE) orders; 
/* Verifico con EXPLAIN che il piano usi effettivamente un Index-Only Scan */
 EXPLAIN (ANALYZE, BUFFERS) SELECT COUNT(*) FROM orders WHERE status =
'completed';
* Dopo il vacuum, il piano deve mostrare "Index Only Scan" e "Heap Fetches: 0"
* */
 
* Monitoro nel tempo: se visibility_pct scende di nuovo rapidamente,
* l'autovacuum è ancora troppo lento */
 SELECT relname, last_autovacuum, n_dead_tup FROM pg_stat_user_tables WHERE
relname = 'orders';
```
