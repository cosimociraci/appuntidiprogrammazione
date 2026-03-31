---
layout: post
title: "Predicate Locking in SSI"
date: 2026-03-31 16:50:23 
sintesi: "Il Predicate Locking è la tecnologia che permette al livello SERIALIZABLE di funzionare. A differenza dei lock normali, non blocca i dati esistenti, ma "segna" le condizioni di ricerca (i predicati). Se una transazione A legge tutti gli utenti "attiv"
tech: db
tags: ['db', 'concorrenza e locking approfond']
pdf_file: "predicate-locking-in-ssi.pdf"
---

## Esigenza Reale
Garantire la coerenza di un sistema di allocazione budget dove la somma delle spese non deve mai superare il tetto massimo, anche se le spese vengono inserite contemporaneamente.

## Analisi Tecnica
Problema: Come bloccare una "condizione" (la somma) invece di singole righe che potrebbero non esistere ancora. Perché: Sfrutto l'infrastruttura SSI di Postgres. Ho scelto questo metodo perché è l'unico che garantisce l'assenza di anomalie senza dover bloccare l'intera tabella dei pagamenti.

## Esempio Implementativo

```db
/* Il database "ricorda" che ho letto questa somma tramite un predicate lock implicito sulla condizione WHERE project_id = 5. Se qualcuno inserisce una spesa sullo stesso progetto prima del mio COMMIT, Postgres rileva la sovrapposizione logica e annulla una delle due transazioni. */ BEGIN ISOLATION LEVEL SERIALIZABLE; /* Leggo il budget disponibile e la spesa corrente. Questi due SELECT creano predicate lock su entrambe le tabelle per le condizioni usate. */ SELECT budget_limit INTO v_limit FROM projects WHERE id = 5 FOR SHARE; SELECT coalesce(sum(amount), 0) INTO v_spent FROM expenses WHERE project_id = 5; /* Verifico il vincolo a livello applicativo prima di inserire. */ IF v_spent + 100 > v_limit THEN RAISE EXCEPTION 'Budget superato: disponibile %, richiesto %', v_limit - v_spent, 100; END IF; INSERT INTO expenses (project_id, amount, description) VALUES (5, 100, 'Acquisto hardware'); COMMIT; /* Monitoro i predicate lock attivi per capire cosa sta proteggendo il sistema in un dato momento: */ SELECT database, relation::regclass, mode, pid FROM pg_locks WHERE locktype IN ('relation', 'page', 'tuple', 'object', 'advisory') AND mode LIKE '%Siread%'; /* SIREAD è il tipo di lock usato da SSI: è invisibile agli altri processi (non li blocca) ma viene confrontato con i nuovi lock per rilevare cicli di dipendenze. */
```
