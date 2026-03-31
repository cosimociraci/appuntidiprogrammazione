---
layout: post
title: Explicit Table Locking (SHARE/EXCLUSIVE)
date: '2026-03-31 16:25:01 '
sintesi: 'Sebbene il locking automatico di Postgres sia eccellente, a volte è necessario
  un controllo manuale tramite il comando LOCK TABLE. Esistono diversi modi: SHARE
  (permette letture, blocca scritture) o EXCLUSIVE (blocca tutto). L''uso di lock
  espliciti è'
esigenza: Sincronizzare un ricalcolo massivo di una classifica utenti dove non voglio
  che nessun voto venga inserito finché il calcolo non è terminato.
tech: db
tags:
- db
- concorrenza e locking approfond
codice: '/* Acquisisco il lock più debole che soddisfa il mio requisito. SHARE blocca
  INSERT/UPDATE/DELETE ma non i SELECT degli altri utenti, minimizzando l''impatto
  sulla concorrenza in lettura. */ BEGIN; LOCK TABLE votes IN SHARE MODE; /* Ricalcolo
  la classifica in modo atomico partendo dai dati "congelati". Nessun voto può essere
  inserito mentre sono qui. */ TRUNCATE user_rankings; INSERT INTO user_rankings (user_id,
  score, rank) SELECT user_id, sum(points) AS score, rank() OVER (ORDER BY sum(points)
  DESC) AS rank FROM votes GROUP BY user_id; /* Rilascio il lock implicitamente con
  il COMMIT. La durata del lock deve essere la minima possibile: preparo i dati in
  una tabella temporanea prima di acquisirlo, ed eseguo solo la TRUNCATE + INSERT
  finale dentro la transazione. */ COMMIT; /* Per confronto, ecco la gerarchia dei
  lock dal meno al più restrittivo: ACCESS SHARE -> ROW SHARE -> ROW EXCLUSIVE ->
  SHARE UPDATE EXCLUSIVE -> SHARE -> SHARE ROW EXCLUSIVE -> EXCLUSIVE -> ACCESS EXCLUSIVE
  Uso ACCESS EXCLUSIVE solo per DDL (ALTER TABLE, DROP, TRUNCATE). */'
---

Problema: La necessità di garantire un'istantanea statica di un'intera tabella per una procedura complessa che non può usare SSI. Perché: Uso LOCK TABLE ... IN SHARE MODE. Ho scelto SHARE perché mi permette di leggere i dati con la certezza che non cambino, pur consentendo ad altri di leggere (ma non scrivere).