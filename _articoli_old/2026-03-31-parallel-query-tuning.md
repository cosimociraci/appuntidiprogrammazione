---
layout: post
title: "Parallel Query Tuning"
date: 2026-03-31 10:11:47 +0200
sintesi: "PostgreSQL può usare più core della CPU per eseguire una singola query tramite i nodi "Gather" e "Parallel Scan". Tuttavia, il parallelismo non è semp..."
tech: db
tags: ['db', 'query opt. & planner']
---
## Esigenza Reale
Sfruttare tutti i core di un server moderno per accelerare il calcolo di aggregati su tabelle da centinaia di milioni di righe.

## Analisi Tecnica
Problema: Query pesanti che utilizzano un solo core mentre gli altri 31 rimangono inattivi. Perché: Ho regolato i parametri di parallelismo. Ho scelto di forzare il parallelismo su questa tabella specifica perché la scansione sequenziale è inevitabile ma può essere divisa tra più worker.

