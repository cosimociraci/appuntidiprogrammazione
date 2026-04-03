---
layout: post
title: "FOR UPDATE NOWAIT"
date: 2026-04-03 14:45:13
sintesi: >
  Quando un'applicazione deve acquisire un lock su una riga per modificarla, il comportamento standard è aspettare se la riga è già bloccata. In scenari interattivi (es. un utente che apre una scheda per modifica), l'attesa può sembrare un blocco del s
tech: "db"
tags: ["db", "concorrenza e locking approfond"]
pdf_file: "for-update-nowait.pdf"
---

## Esigenza Reale
Implementare un sistema di editing collaborativo "ottimista" dove il primo che arriva blocca la risorsa e gli altri vengono avvisati subito.

## Analisi Tecnica
Problema: L'utente rimane in attesa indefinita se un altro processo ha lasciato una transazione appesa su quel record. Perché: Uso FOR UPDATE NOWAIT. Ho scelto questa opzione perché voglio un feedback immediato: se non posso avere il lock, l'applicazione deve gestire l'errore 54P01 istantaneamente.

## Esempio Implementativo

```sql
* Tento il lock sulla riga. Se un altro utente la sta modificando, Postgres
* lancia immediatamente un'eccezione senza attendere, che catturo a livello
* applicativo. */
 BEGIN; SELECT id, title, content, version FROM documents WHERE id = 1024 FOR
UPDATE NOWAIT;
* Se arrivo qui, il record è mio. Procedo con la modifica includendo il campo
* 'version' per un ottimistic locking di secondo livello. */
 UPDATE documents SET content = 'nuovo contenuto', version = version + 1,
updated_at = now() WHERE id = 1024 AND version = 3; -- Controllo che version non
sia cambiata nel frattempo GET DIAGNOSTICS rows_affected = ROW_COUNT; IF
rows_affected = 0 THEN RAISE EXCEPTION 'Conflitto di versione: il documento è
stato modificato da un altro utente.'; END IF; COMMIT;
* A livello applicativo (Java/Spring), gestisco l'eccezione PSQLException con
* SQLSTATE 55P03 (lock_not_available): try
{ documentRepository.lockAndUpdate(docId, content, version); }
 catch (PSQLException e) 
{ if ("55P03".equals(e.getSQLState())) 
{ 
// Restituisco HTTP 409 Conflict con messaggio leggibile dall'utente throw new
// DocumentLockedException("Il documento è in uso da un altro operatore."); }
 }
 */
 
* In alternativa a NOWAIT, SKIP LOCKED è utile per sistemi a coda (job queue):
* SELECT * FROM tasks WHERE status = 'pending' ORDER BY created_at FOR UPDATE
* SKIP LOCKED LIMIT 1; -- Ogni worker prende un task diverso senza bloccarsi a
* vicenda */
```
