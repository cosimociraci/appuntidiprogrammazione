---
layout: post
title: Statistics Target e Selettività
date: '2026-03-31 16:25:01 '
sintesi: La qualità del piano dipende dalla precisione degli istogrammi salvati nelle
  statistiche. Per impostazione predefinita, Postgres campiona 100 valori comuni per
  ogni colonna. Per colonne con distribuzioni di dati molto irregolari (es. pochi
  clienti co
esigenza: Correggere piani di esecuzione errati su colonne che contengono dati con
  una distribuzione "long tail".
tech: db
tags:
- db
- query opt. & planner
codice: ''
---

Problema: Il Planner sbaglia completamente la stima delle righe perché l'istogramma delle statistiche è troppo approssimativo. Perché: Ho alzato il target delle statistiche solo per la colonna problematica. Ho scelto questa via per non appesantire il processo globale di ANALYZE, ma risolvere il problema alla radice per le query critiche.