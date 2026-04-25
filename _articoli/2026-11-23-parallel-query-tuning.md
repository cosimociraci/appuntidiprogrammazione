---
layout: code
title: "Parallel Query Tuning"
date: 2026-11-23 12:00:00
sintesi: >
  PostgreSQL può usare più core della CPU per eseguire una singola query tramite i nodi "Gather" e "Parallel Scan". Tuttavia, il parallelismo non è sempre un vantaggio: creare e coordinare i worker ha un costo. Se la tabella è piccola o se max_parallel
tech: "sql"
tags: ["sql", "db"]
pdf_file: "parallel-query-tuning.pdf"
---

## Esigenza Reale
Sfruttare tutti i core di un server moderno per accelerare il calcolo di aggregati su tabelle da centinaia di milioni di righe.

## Analisi Tecnica
**Problema:** Query pesanti che utilizzano un solo core mentre gli altri 31 rimangono inattivi.

**Perché:** Ho regolato i parametri di parallelismo. Ho scelto di forzare il parallelismo su questa tabella specifica perché la scansione sequenziale è inevitabile ma può essere divisa tra più worker.


## Esempio Pratico: Accelerare un'aggregazione su Large Table

Supponiamo di avere una tabella `telemetry_data` con 200 milioni di record. Una query di reportistica che calcola la media dei valori giornalieri impiega troppo tempo perché il Planner sceglie un piano seriale, ritenendo che il costo di gestione dei worker superi il beneficio.



### 1. Diagnosi del collo di bottiglia
Eseguendo un `EXPLAIN`, notiamo che viene utilizzato un singolo processo.

```sql
-- La query è lenta e usa un solo core
EXPLAIN SELECT sensor_id, AVG(reading) 
FROM telemetry_data 
GROUP BY sensor_id;
```

### 2. Tuning dei parametri di soglia
Se il Planner è troppo "pigro" nel lanciare worker paralleli, possiamo abbassare le barriere all'ingresso o forzare la scala sulla tabella specifica.

```sql
-- Rendo meno costoso l'avvio dei worker paralleli (tuning fine)
SET parallel_tuple_cost = 0.01; -- Default 0.1
SET parallel_setup_cost = 100; -- Default 1000

-- Comunico al Planner che questa tabella specifica beneficia di più worker
ALTER TABLE telemetry_data SET (parallel_workers = 8);

-- Verifico che il limite globale consenta l'operazione
-- SHOW max_parallel_workers_per_gather; 
```

### 3. Risultato nel Piano di Esecuzione
Dopo la modifica, il piano di esecuzione cambierà drasticamente:

* **Parallel Seq Scan:** Invece di un solo processo che legge l'intero file, 8 worker leggono porzioni diverse della tabella contemporaneamente.
* **Partial Aggregate:** Ogni worker calcola una media parziale sui propri dati.
* **Gather:** Un nodo "collettore" riceve i risultati parziali dai worker.
* **Finalize Aggregate:** Il processo principale combina i risultati parziali per fornire il dato finale.

**Risultato:** Su un server con 32 core, questo approccio può ridurre il tempo di esecuzione di oltre il 70%, trasformando un'attesa di minuti in una di pochi secondi, saturando correttamente le risorse hardware disponibili senza influenzare negativamente le query più piccole.

---