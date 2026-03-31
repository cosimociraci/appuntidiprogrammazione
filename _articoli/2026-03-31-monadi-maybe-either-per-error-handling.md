---
layout: post
title: "Monadi (Maybe, Either) per Error Handling"
date: 2026-03-31 16:50:23 
sintesi: "L'abuso di try...catch e controlli if(null) sporca il dominio core. Il pattern Either incapsula effetti collaterali e potenziali fallimenti: Left rappresenta l'errore, Right il successo. Questo permette di concatenare operazioni (.map, .chain) in una"
tech: js
tags: ['js', 'design patterns & architecture']
pdf_file: "monadi-maybe-either-per-error-handling.pdf"
---

## Esigenza Reale
Validare e processare input utente complessi attraverso una serie di trasformazioni che possono fallire silenziosamente.

## Analisi Tecnica
Problema: Codice "spaghetto" dovuto a controlli di errore annidati e gestione incoerente delle eccezioni asincrone. Perché: Uso programmazione funzionale tipizzata. Ho scelto le monadi per rendere il flusso dei dati esplicito e deterministico, eliminando i branch condizionali multipli.

## Esempio Implementativo

```js
/* Implemento il contenitore Either completo con i metodi fondamentali. */ const Right = value => ({ isRight: true, isLeft: false, map: fn => Right(fn(value)), // Applica fn se sono Right chain: fn => fn(value), // Come map ma fn restituisce già un Either getOrElse: _ => value, // Estrae il valore ignorando il default fold: (leftFn, rightFn) => rightFn(value), // Applica la funzione di destra toString: () => `Right(${value})` }); const Left = error => ({ isRight: false, isLeft: true, map: _ => Left(error), // Cortocircuito: ignoro fn e propago l'errore chain: _ => Left(error), // Cortocircuito: stesso comportamento getOrElse: defaultVal => defaultVal, // Estrae il default poiché sono in errore fold: (leftFn, _) => leftFn(error), // Applica la funzione di sinistra toString: () => `Left(${error})` }); /* Helper per convertire valori nullable in Either. */ const fromNullable = value => value != null ? Right(value) : Left('Valore nullo o undefined'); /* Helper per wrappare funzioni che possono lanciare eccezioni. */ const tryCatch = fn => { try { return Right(fn()); } catch (e) { return Left(e.message); } }; /* Pipeline di validazione che usa Either per gestire gli errori senza try/catch. */ function validateEmail(email) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? Right(email) : Left('Email non valida: ' + email); } function validateAge(age) { return Number.isInteger(age) && age >= 18 && age <= 120 ? Right(age) : Left('Età non valida: deve essere tra 18 e 120'); } function validateName(name) { return typeof name === 'string' && name.trim().length >= 2 ? Right(name.trim()) : Left('Nome non valido: minimo 2 caratteri'); } /* Compongo la validazione in una pipeline: il primo Left cortocircuita l'intera catena. */ function validateUserInput(rawInput) { return fromNullable(rawInput) .chain(input => validateName(input.name) .chain(name => validateEmail(input.email) .chain(email => validateAge(input.age) .map(age => ({ name, email, age })) // Costruisco l'oggetto validato ))); } /* Uso la pipeline nella gestione delle richieste Express senza nessun try/catch. */ app.post('/users', (req, res) => { validateUserInput(req.body) .chain(validData => tryCatch(() => db.users.create(validData))) .fold( error => res.status(400).json({ success: false, error }), user => res.status(201).json({ success: true, user }) ); }); /* Per operazioni asincrone, implemento AsyncEither (o uso una libreria come fp-ts). */ const AsyncRight = value => ({ map: async fn => AsyncRight(await fn(value)), chain: async fn => fn(value), fold: async (leftFn, rightFn) => rightFn(value) }); /* Esempio di pipeline asincrona senza try/catch: */ async function processRegistration(rawInput) { return validateUserInput(rawInput) .chain(async validData => { const exists = await db.users.findByEmail(validData.email); return exists ? Left('Email già registrata') : Right(validData); }) .chain(async data => { const user = await db.users.create(data); await emailService.sendWelcome(user.email); return Right(user); }); }
```
