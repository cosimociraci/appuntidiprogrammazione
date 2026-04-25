---
layout: code
title: "Event Sourcing e State Reconstitution"
date: 2026-07-08 12:00:00
sintesi: >
  Gestire lo stato attuale non permette di capire come ci si è arrivati (audit log). L'Event Sourcing non salva lo stato, ma una sequenza immutabile di eventi (append-only). Lo stato attuale viene ricostruito ("proiezione") riducendo (folding) l'array 
tech: "javascript"
tags: ["javascript"]
pdf_file: "event-sourcing-e-state-reconstitution.pdf"
---

## Esigenza Reale
Implementare un sistema di carrello acquisti dove ogni aggiunta, rimozione o modifica deve essere tracciabile e reversibile.

## Analisi Tecnica
**Problema:** Perdita di contesto storico sullo stato dell'applicazione e difficoltà nel gestire la persistenza offline complessa.

**Perché:** Implemento un registro di eventi. Ho scelto questo pattern per garantire l'integrità dei dati e permettere la sincronizzazione parziale tra client e server basata su delta di eventi.

## Esempio Implementativo

```javascript
/* Definisco i tipi di evento del dominio. Gli eventi sono immutabili e
    descrivono COSA è successo, non COME. */
const EventTypes = Object.freeze({
    ITEM_ADDED: 'ITEM_ADDED', ITEM_REMOVED: 'ITEM_REMOVED', QUANTITY_CHANGED:
        'QUANTITY_CHANGED', CART_CLEARED: 'CART_CLEARED', COUPON_APPLIED:
        'COUPON_APPLIED'
}
);
/* Il reducer è una funzione pura che applica un evento allo stato corrente. */
function cartReducer(state, event) {
    switch (event.type) {
        case EventTypes.ITEM_ADDED: return {
            ...state, items: [...state.items, {
                id: event.itemId, quantity: 1, price: event.price, name:
                    event.name
            }
            ]
        }
        ;
        case EventTypes.ITEM_REMOVED: return {
            ...state, items: state.items.filter(item => item.id !==
                event.itemId)
        }
        ;
        case EventTypes.QUANTITY_CHANGED: return {
            ...state, items: state.items.map(item => item.id === event.itemId ?
                {
                ...item, quantity: event.quantity
            }
            : item )
        }
        ;
        case EventTypes.CART_CLEARED: return {
            ...state, items: [], coupon: null
        }
        ;
        case EventTypes.COUPON_APPLIED: return {
            ...state, coupon: {
                code: event.code, discount: event.discount
            }
        }
        ;
        default: return state;
    }
}
/* Ricostruisco lo stato attuale riducendo l'intera sequenza di eventi: "fold" o
    "replay". */
function reconstitute(events, initialState = {
    items: [], coupon: null
}
) {
    return events.reduce(cartReducer, initialState);
}
/* Implemento il carrello come Event Store con replay e time travel. */
class ShoppingCart {
    constructor(cartId) {
        this.cartId = cartId;
        this.events = [];
        // Log immutabile degli eventi this._state =
        {
            items: [], coupon: null
        }
        ;
        // Stato proiettato
    }
    // Ogni "comando" genera un evento e aggiorna lo stato addItem(itemId, name,
        price)
    {
        const event = {
            type: EventTypes.ITEM_ADDED, itemId, name, price, timestamp:
                Date.now(), version: this.events.length + 1
        }
        ;
        this.events.push(event);
        this._state = cartReducer(this._state, event);
        return this;
    }
    removeItem(itemId) {
        const event = {
            type: EventTypes.ITEM_REMOVED, itemId, timestamp: Date.now(),
                version: this.events.length + 1
        }
        ;
        this.events.push(event);
        this._state = cartReducer(this._state, event);
        return this;
    }
    // Time Travel: ricostruisco lo stato a un istante preciso nel passato
        getStateAt(timestamp)
    {
        const eventsUpTo = this.events.filter(e => e.timestamp <= timestamp);
        return reconstitute(eventsUpTo);
    }
    // Snapshot: ottimizzazione per non rifare il replay dall'inizio ogni volta
        createSnapshot()
    {
        return {
            state: this._state, version: this.events.length, timestamp:
                Date.now()
        }
        ;
    }
    // Restore da snapshot + eventi successivi restoreFromSnapshot(snapshot,
        laterEvents)
    {
        const baseState = snapshot.state;
        const newEvents = laterEvents.filter(e => e.version > snapshot.version);
        this._state = reconstitute(newEvents, baseState);
        this.events = laterEvents;
    }
    get state() {
        return this._state;
    }
    get total() {
        const subtotal = this._state.items.reduce((sum, item) => sum +
            item.price * item.quantity, 0);
        const discount = this._state.coupon ? subtotal *
            this._state.coupon.discount : 0;
        return subtotal - discount;
    }
}
/* Sincronizzazione offline: invio solo i delta di eventi al server, non lo
    stato completo. */
async function syncCartWithServer(cart, lastSyncedVersion) {
    const newEvents = cart.events.filter(e => e.version > lastSyncedVersion);
    if (newEvents.length === 0) return;
    await fetch('/api/cart/events', {
        method: 'POST', headers: {
            'Content-Type': 'application/json'
        }
        , body: JSON.stringify({
            cartId: cart.cartId, events: newEvents
        }
        )
    }
    );
}
```
