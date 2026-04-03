---
layout: post
title: "WAL Archiving & Point-In-Time Recovery (PITR)"
date: 2026-04-03 14:45:23
sintesi: >
  Il PITR permette di riportare il database a un istante preciso nel passato (es. un secondo prima di un DROP TABLE accidentale). Il flusso si basa su due componenti: un base backup periodico unito a una catena ininterrotta di file WAL archiviati. L'af
tech: "db"
tags: ["db", "advanced replication & ha"]
pdf_file: "wal-archiving-point-in-time-recovery-pitr.pdf"
---

## Esigenza Reale
Recuperare i dati dopo che un errore nel codice applicativo ha corrotto migliaia di record alle ore 10:15 di mattina.

## Analisi Tecnica
Problema: Impossibilità di recuperare dati cancellati per errore se non si dispone della sequenza esatta dei cambiamenti dal momento del backup. Perché: Configuro l'archiviazione continua dei WAL. Ho scelto di usare pgBackRest perché gestisce nativamente la compressione, la verifica dell'integrità e i retry degli archivi meglio di uno script manuale.

## Esempio Implementativo

```sql
* Nel postgresql.conf abilito l'archiviazione WAL verso una destinazione remota
* sicura. */
 -- archive_mode = on -- archive_command = 'pgbackrest --stanza=myapp archive-
push %p' -- wal_level = replica -- Minimo necessario per l'archiviazione
/* Eseguo il base backup iniziale con pgBackRest: */
 -- pgbackrest --stanza=myapp --type=full backup 
/* Verifico che l'archivio WAL sia continuo e integro: */
 -- pgbackrest --stanza=myapp info 
* In caso di corruzione dei dati, avvio il ripristino su un server separato
* specificando il target temporale (un minuto prima del disastro): */
 -- pgbackrest --stanza=myapp --type=time "--target=2026-03-25 10:14:00+01"
restore
* Creo il file recovery.signal per attivare la modalità di recovery e specifico
* il target nel postgresql.conf del server di ripristino: */
 -- recovery_target_time = '2026-03-25 10:14:00+01' -- recovery_target_action =
'promote' -- Una volta raggiunto il target, promuove il DB a primario
* Verifico la continuità della catena WAL controllando che non ci siano buchi
* nella sequenza dei file archiviati: */
 SELECT wal_filename, archived_count, failed_count, last_archived_wal,
last_archived_time, last_failed_wal, last_failed_time FROM pg_stat_archiver;
* Se last_failed_wal è valorizzato, l'archiviazione ha avuto problemi: forzo
* manualmente il retry sull'ultimo WAL fallito. */
 SELECT pg_switch_wal(); -- Forza la chiusura del WAL segment corrente e il
tentativo di archiviazione
* In Spring Boot, schedulo un job che verifica quotidianamente l'integrità
* dell'archivio e la freschezza dell'ultimo backup: @Scheduled(cron = "0 0 6 * *
* *")
// Ogni mattina alle 06:00 public void verifyBackupHealth() 
{ try 
{ Process p = Runtime.getRuntime().exec("pgbackrest --stanza=myapp check"); int
exit = p.waitFor(); if (exit != 0)
{ alertService.sendCritical("pgBackRest check fallito: backup PITR non
affidabile"); }
 }
 catch (Exception e) 
{ alertService.sendCritical("Impossibile verificare il backup: " +
e.getMessage()); }
 }
 */
```
