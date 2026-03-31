---
layout: post
title: Hidden Classes (Shapes) e Inline Caching
date: '2026-03-31 16:25:01 '
sintesi: 'V8 non usa dizionari per gli oggetti ma "Hidden Classes". Inizializzare
  proprietà in ordine diverso o aggiungerle dinamicamente rompe la "Shape", forzando
  il motore a creare nuove classi nascoste. Questo invalida l''Inline Cache (IC):
  se la Shape camb'
esigenza: Ottimizzare il throughput di un server che manipola milioni di oggetti "User"
  simili in loop stretti.
tech: js
tags:
- js
- v8 engine & runtime performance
codice: '/* PATTERN SBAGLIATO: aggiungo proprietà dopo la costruzione, rompendo la
  Hidden Class. V8 crea una nuova Shape per ogni variante, invalidando l''Inline Cache
  per tutte le funzioni che toccano questi oggetti. */ class UserBad { constructor(id,
  name) { this.id = id; this.name = name; // Nessuna altra proprietà } } const u1
  = new UserBad(1, ''Alice''); u1.metadata = { role: ''admin'' }; // Shape #1: {id,
  name, metadata} const u2 = new UserBad(2, ''Bob''); u2.lastLogin = new Date(); //
  Shape #2: {id, name, lastLogin} // Ora qualsiasi funzione che accetta UserBad è
  polimorfica: V8 deve gestire più Shape /* PATTERN CORRETTO: inizializzo tutti i
  campi nel costruttore, anche se null. V8 crea una sola Hidden Class e può usare
  il Monomorphic Inline Cache per tutti gli accessi. */ class User { constructor(id,
  name) { // Inizializzo TUTTI i campi noti nel costruttore e nello stesso ordine.
  // V8 crea una transizione di Shape lineare: C0 -> C1(id) -> C2(id,name) -> C3(id,name,metadata)
  -> C4(id,name,metadata,lastLogin) this.id = id; this.name = name; this.metadata
  = null; // Placeholder: evita l''aggiunta dinamica successiva this.lastLogin = null;
  // Stessa Shape per tutte le istanze } } const u3 = new User(3, ''Carol''); u3.metadata
  = { role: ''admin'' }; // Aggiorno un campo esistente: Shape invariata const u4
  = new User(4, ''Dave''); u4.lastLogin = new Date(); // Aggiorno un campo esistente:
  Shape invariata /* Verifico in Node.js se un oggetto è in Dictionary Mode (la peggiore
  condizione): */ // node --allow-natives-syntax app.js function checkShape(obj) {
  // %HasFastProperties è una funzione interna di V8 esposta con --allow-natives-syntax
  if (!%HasFastProperties(obj)) { console.warn(''ATTENZIONE: oggetto in Dictionary
  Mode!'', Object.keys(obj)); } } /* Per processare milioni di oggetti User in un
  loop stretto, la stabilità della Shape è critica. Con la Shape monomorfica, V8 ottimizza
  l''intero loop con TurboFan: */ function processUsers(users) { let totalId = 0;
  for (let i = 0; i < users.length; i++) { // V8 sa che users[i].id è sempre un intero
  in offset fisso: accesso O(1) totale // Con Shape polimorfica, ogni accesso richiederebbe
  un hash lookup totalId += users[i].id; } return totalId; } // Pre-riscaldo la funzione
  con il tipo corretto per stabilizzare il Monomorphic IC const sampleUsers = Array.from({
  length: 10 }, (_, i) => new User(i, `User${i}`)); processUsers(sampleUsers); //
  Warmup: TurboFan ottimizza per la Shape di User /* In un server Express/Node.js
  che riceve JSON dall''esterno, normalizzo sempre gli oggetti prima di processarli
  per garantire la stabilità della Shape: */ function normalizeUserFromJson(rawJson)
  { // Creo SEMPRE un''istanza User con il costruttore: mai usare rawJson direttamente
  nei loop return new User( rawJson.id ?? 0, rawJson.name ?? '''', rawJson.metadata
  ?? null, rawJson.lastLogin ? new Date(rawJson.lastLogin) : null ); }'
---

Problema: Calo drastico delle performance dovuto alla polimorfizzazione delle funzioni che accettano oggetti con strutture (shapes) leggermente diverse. Perché: Mantengo la stabilità delle forme. Ho scelto di inizializzare tutti i campi nel costruttore, anche come null, per garantire che ogni istanza condivida la stessa transizione di classe nascosta.