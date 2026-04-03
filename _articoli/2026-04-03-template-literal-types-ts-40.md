---
layout: post
title: "Template Literal Types (TS 4.0+)"
date: 2026-04-03 14:40:03
sintesi: "Manipolare stringhe a livello di tipo per validare pattern testuali. Combinando stringhe con la sintassi `${A}${B}`  possibile generare set di tipi dinamici. Questo permette di tipizzare con precisione millimetrica eventi, percorsi di routing o stil"
tech: "js"
tags: ["js", "typescript & advanced types"]
pdf_file: "template-literal-types-ts-40.pdf"
---

## Esigenza Reale
Creare un Event Emitter dove i nomi degli eventi sono generati automaticamente come user_created, user_deleted, ecc.

## Analisi Tecnica
Problema: Perdita di type-safety quando si usano stringhe dinamiche come chiavi o identificatori. Perché: Uso i Template Literal Types. Ho scelto di automatizzare la creazione di tipi stringa per evitare errori di battitura in sistemi basati su convenzioni di naming.

## Esempio Implementativo

```js
* Template Literal Types: combino tipi stringa letterali per generare nuovi
* tipi. */
 type Entity = 'user' | 'order' | 'product' | 'invoice'; type Action = 'created'
| 'updated' | 'deleted' | 'archived';
// Genero automaticamente tutte le combinazioni: "user_created" | "user_updated"
// | ... (16 tipi) type DomainEvent = `$
{Entity}
_$
{Action}
`; 
// TypeScript genera l'intero prodotto cartesiano delle stringhe 
// Utilizzo: solo stringhe valide sono accettate const validEvent: DomainEvent =
// 'user_created';
// OK const invalidEvent: DomainEvent = 'user_destroyed'; 
// Errore TS: not assignable to type 'DomainEvent' 
/* Creo un Event Emitter fortemente tipizzato con Template Literal Types. */
 
// Mappa evento -> tipo del payload type EventPayloadMap = 
{ user_created: 
{ id: number; name: string; email: string }
; user_updated: 
{ id: number; changes: Partial<
{ name: string; email: string }
> }
; user_deleted: 
{ id: number; deletedAt: Date }
; order_created: 
{ orderId: string; userId: number; total: number }
; order_updated: 
{ orderId: string; status: 'pending' | 'shipped' | 'delivered' }
; order_deleted: 
{ orderId: string; reason: string }
; }
; class TypedEventEmitter 
{ private handlers = new Map<string, Set<Function>>(); 
// Il tipo del handler è inferito dal nome dell'evento: zero cast on(event: E,
// handler: (payload: EventPayloadMap[E]) => void): () => void
{ if (!this.handlers.has(event)) 
{ this.handlers.set(event, new Set()); }
 this.handlers.get(event)!.add(handler); 
// Ritorno la funzione di unsubscribe return () =>
// this.handlers.get(event)?.delete(handler); }
 emit(event: E, payload: EventPayloadMap[E]): void 
{ this.handlers.get(event)?.forEach(handler => handler(payload)); }
 }
 const emitter = new TypedEventEmitter(); 
// TypeScript inferisce automaticamente il tipo del payload dall'evento
// emitter.on('user_created', (payload) =>
{ 
// payload: 
{ id: number; name: string; email: string }
 console.log(`Nuovo utente: $
{payload.name}
 ($
{payload.email}
)`); }
); emitter.emit('user_created', 
{ id: 1, name: 'Alice', email: 'alice@example.com' }
); 
// OK emitter.emit('user_created', 
{ id: 1, name: 'Alice' }
); 
// Errore TS: manca 'email' 
/* Template Literal Types per routing type-safe: */
 type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'; type ApiRoute =
`/api/$
{string}
`; type RouteKey = `$
{HttpMethod}
 $
{ApiRoute}
`; 
// Registro i route handler con tipo validato a compile time const routes = new
// Map<RouteKey, Function>(); function registerRoute(key: RouteKey, handler:
// Function)
{ routes.set(key, handler); }
 registerRoute('GET /api/users', () => 
{}
); 
// OK registerRoute('POST /api/orders', () => 
{}
); 
// OK registerRoute('INVALID /api/users', () => 
{}
); 
// Errore TS: 'INVALID' non è un HttpMethod 
/* Template Literal Types per CSS properties type-safe: */
 type Side = 'top' | 'right' | 'bottom' | 'left'; type SpacingProperty = `$
{'margin' | 'padding'}
-$
{Side}
`; 
// "margin-top" | "margin-right" | ... | "padding-left" (8 tipi) type CSSValue =
// `$
{number}
$
{'px' | 'rem' | 'em' | '%'}
`; type StyleObject = Partial<Record<SpacingProperty, CSSValue>>; function
applyStyles(element: HTMLElement, styles: StyleObject): void
{ (Object.entries(styles) as [SpacingProperty, CSSValue][]).forEach(([prop,
value]) =>
{ element.style.setProperty(prop, value); }
); }
 applyStyles(document.body, 
{ 'margin-top': '16px', 
// OK 'padding-left': '1rem', 
// OK 'margin-center': '8px', 
// Errore TS: 'margin-center' non è una SpacingProperty }
);
```
