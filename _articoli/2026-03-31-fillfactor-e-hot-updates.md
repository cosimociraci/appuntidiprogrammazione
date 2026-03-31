---
layout: post
title: "Fillfactor e HOT Updates"
date: 2026-03-31 16:39:58 
tech: db
tags: ['db', 'vacuum & storage']
pdf_file: "fillfactor-e-hot-updates.pdf"
---

## Esigenza Reale
Ottimizzare una tabella di contatori o stati che viene aggiornata frequentemente, evitando l'overhead di scrittura sugli indici a ogni modifica.

## Analisi Tecnica
Problema: Ogni aggiornamento di riga genera una nuova voce in tutti gli indici della tabella, raddoppiando il lavoro di I/O. Perché: Uso un fillfactor ridotto. Ho scelto di sacrificare un po' di spazio disco per permettere gli HOT updates, garantendo che le versioni aggiornate delle righe restino nella stessa pagina fisica.

## Esempio Implementativo

```db
/* Imposto il fillfactor al 90% per lasciare spazio agli HOT update */ ALTER TABLE counters SET (fillfactor = 90); /* La modifica diventa effettiva solo dopo una riscrittura: eseguo VACUUM FULL o pg_repack */ VACUUM FULL counters; /* Verifico il rapporto tra update normali e HOT update: più n_tup_hot_upd si avvicina a n_tup_upd, meglio è */ SELECT relname, n_tup_upd, n_tup_hot_upd, round(n_tup_hot_upd::numeric / NULLIF(n_tup_upd, 0) * 100, 2) AS hot_pct FROM pg_stat_user_tables WHERE relname = 'counters'; /* Se hot_pct < 50%, verifico che le colonne aggiornate non siano indicizzate: gli HOT update sono impossibili su colonne con indice */ SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'counters'; /* Esempio di update che genera HOT: aggiorno solo 'valore', colonna non indicizzata */ UPDATE counters SET valore = valore + 1 WHERE id = 42;
```
