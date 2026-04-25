---
layout: code
title: "Statistics Target e Selettività"
date: 2026-11-11 12:00:00
sintesi: >
  La qualità del piano dipende dalla precisione degli istogrammi salvati nelle statistiche. Per impostazione predefinita, Postgres campiona 100 valori comuni per ogni colonna. Per colonne con distribuzioni di dati molto irregolari (es. pochi clienti co
tech: "sql"
tags: ["sql", "db", "analyze", "performance"]
pdf_file: "statistics-target-e-selettivit.pdf"
---

## Esigenza Reale
Correggere piani di esecuzione errati su colonne che contengono dati con una distribuzione "long tail".

## Analisi Tecnica
**Problema:** Il Planner sbaglia completamente la stima delle righe perché l'istogramma delle statistiche è troppo approssimativo.

**Perché:** Ho alzato il target delle statistiche solo per la colonna problematica. Ho scelto questa via per non appesantire il processo globale di ANALYZE, ma risolvere il problema alla radice per le query critiche.

## Esempio Pratico: Ottimizzazione di una colonna "Stato Ordine"

Immaginiamo di avere una tabella `orders` dove la colonna `status` ha una distribuzione estremamente sbilanciata: milioni di righe con stato 'PROCESSED' e solo poche centinaia con stato 'PENDING'. Con il `statistics target` predefinito (100), Postgres potrebbe sottostimare drasticamente le righe 'PENDING', scegliendo un **Sequential Scan** invece di un **Index Scan**.

### 1. Verifica della situazione attuale
Per prima cosa, controllo quante righe il planner "pensa" di trovare rispetto alla realtà.

```sql
-- Vedo quante righe stima il planner per gli ordini in attesa
EXPLAIN ANALYZE 
SELECT * FROM orders WHERE status = 'PENDING';
```

### 2. Intervento mirato
Se la stima è molto distante dal valore reale (es. stima 10 righe ma sono 500), aumento la risoluzione dell'istogramma solo per quella colonna specifica.

```sql
-- Incremento il dettaglio delle statistiche per la colonna status a 500 bucket
-- Invece dei 100 di default di sistema
ALTER TABLE orders ALTER COLUMN status SET STATISTICS 500;

-- Rieseguo il campionamento per aggiornare i cataloghi con il nuovo target
ANALYZE orders;
```

### 3. Risultato
Dopo l'operazione, Postgres avrà una "mappa" molto più granulare della distribuzione dei valori.

* **Cosa è cambiato:** L'istogramma ora cattura meglio i valori meno frequenti (la "long tail").
* **Vantaggio:** Il Planner ora riconosce che 'PENDING' è una condizione selettiva e utilizzerà correttamente l'indice non-clustered, riducendo i tempi di risposta della query da secondi a millisecondi.
* **Efficienza:** Avendo modificato solo `status`, le operazioni di `ANALYZE` quotidiane sul resto della tabella rimangono rapide.

---