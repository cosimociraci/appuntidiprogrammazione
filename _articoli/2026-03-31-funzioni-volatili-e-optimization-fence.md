---
layout: post
title: "Funzioni Volatili e Optimization Fence"
date: 2026-03-31 18:55:02 
sintesi: "Le funzioni in Postgres hanno tre livelli di volatilità: VOLATILE, STABLE e IMMUTABLE. Il Planner tratta diversamente le query che le contengono. Una funzione definita erroneamente come VOLATILE (il default) impedisce al Planner di ottimizzare la que"
tech: db
tags: [db, "query opt. & planner"]
pdf_file: "funzioni-volatili-e-optimization-fence.pdf"
---

## Esigenza Reale
Evitare che il database chiami una funzione di conversione valuta 1 milione di volte quando potrebbe farlo una volta sola per l'intera query.

## Analisi Tecnica
Problema: Degrado prestazionale dovuto all'impossibilità del Planner di ottimizzare o "cacheare" i risultati delle funzioni. Perché: Ho marcato la funzione come IMMUTABLE. Ho scelto questo approccio perché i dati di input determinano univocamente l'output, permettendo al Planner di ottimizzare aggressivamente.

## Esempio Implementativo

```db
/* Dimostro l'impatto della volatilità con un esempio concreto. Questa funzione è VOLATILE per default: il Planner la chiama una volta per riga, anche se l'input è costante. */ CREATE OR REPLACE FUNCTION convert_currency(amount numeric, from_cur text, to_cur text) RETURNS numeric AS $$ SELECT amount * rate FROM exchange_rates WHERE from_currency = from_cur AND to_currency = to_cur; $$ LANGUAGE SQL VOLATILE; -- VOLATILE = chiamata 1 milione di volte su 1 milione di righe /* La marco come STABLE: il database la chiama una volta per scansione invece che per riga, perché sa che non cambierà nell'arco della stessa transazione. È corretta perché exchange_rates non cambia durante una query. */ CREATE OR REPLACE FUNCTION convert_currency(amount numeric, from_cur text, to_cur text) RETURNS numeric AS $$ SELECT amount * rate FROM exchange_rates WHERE from_currency = from_cur AND to_currency = to_cur; $$ LANGUAGE SQL STABLE; /* Per funzioni che dipendono solo dai parametri (nessun accesso a tabelle), uso IMMUTABLE: il Planner può pre-calcolarla, usarla negli indici e condividere il risultato tra le righe. */ CREATE OR REPLACE FUNCTION clean_string(input text) RETURNS text AS $$ SELECT trim(lower(input)); $$ LANGUAGE SQL IMMUTABLE; /* Grazie a IMMUTABLE posso creare un indice funzionale: */ CREATE INDEX idx_users_clean_username ON users (clean_string(username)); /* La query userà l'indice solo se la funzione nell'indice e nella WHERE sono identiche: */ SELECT * FROM users WHERE clean_string(username) = 'admin'; /* Verifico la volatilità delle funzioni esistenti per trovare candidati da ottimizzare: */ SELECT proname, provolatile, -- 'v'=volatile, 's'=stable, 'i'=immutable prosrc FROM pg_proc WHERE pronamespace = 'public'::regnamespace ORDER BY proname;
```
