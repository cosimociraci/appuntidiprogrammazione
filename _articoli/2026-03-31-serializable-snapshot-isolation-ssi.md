---
layout: post
title: "Serializable Snapshot Isolation (SSI)"
date: 2026-03-31 17:02:46 
sintesi: "Il livello di isolamento SERIALIZABLE in PostgreSQL non si limita a bloccare le righe, ma monitora le dipendenze tra le transazioni per prevenire anomalie di "vizio di scrittura" (write skew). Mentre REPEATABLE READ garantisce che i dati letti non ca"
tech: db
tags: ['db', 'concorrenza e locking approfond']
pdf_file: "serializable-snapshot-isolation-ssi.pdf"
---

## Esigenza Reale
Gestire un sistema di prenotazione medica dove un medico non può avere più di 10 appuntamenti al giorno, evitando che due inserimenti simultanei superino il limite.

## Analisi Tecnica
Problema: Il controllo del conteggio (COUNT) in una transazione non vede gli inserimenti "in volo" di altre transazioni concorrenti. Perché: Uso il livello SERIALIZABLE. Ho scelto questa strada perché il database rileva automaticamente il conflitto logico tra la lettura del conteggio e l'inserimento, senza che io debba usare lock pesanti su intere tabelle.

## Esempio Implementativo

```db
/* Imposto il livello di isolamento più alto. Se un'altra transazione inserisce un appuntamento per lo stesso medico mentre io sto contando, Postgres fallirà il mio COMMIT con SQLSTATE 40001 "could not serialize access". */ BEGIN ISOLATION LEVEL SERIALIZABLE; /* Leggo il conteggio corrente degli appuntamenti del medico. Questa lettura crea implicitamente un predicate lock sulla condizione WHERE, non solo sulle righe esistenti. */ SELECT count(*) INTO v_count FROM appuntamenti WHERE medico_id = 1 AND data = '2026-05-10'; /* Se la soglia non è raggiunta, procedo con l'inserimento. La combinazione lettura+scrittura nella stessa transazione SERIALIZABLE è ciò che Postgres monitora per rilevare il conflitto. */ IF v_count < 10 THEN INSERT INTO appuntamenti (medico_id, paziente_id, data) VALUES (1, 42, '2026-05-10'); END IF; COMMIT; /* A livello applicativo (Java/JDBC) devo gestire il retry sulla serialization failure: try { eseguiPrenotazione(); } catch (PSQLException e) { if ("40001".equals(e.getSQLState())) { Thread.sleep(50 + random.nextInt(100)); eseguiPrenotazione(); // Riprovo con backoff } } */
```
