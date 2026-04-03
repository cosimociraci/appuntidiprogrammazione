---
layout: post
title: "Discriminated Unions ed Exhaustiveness Checking"
date: 2026-04-03 14:44:54
sintesi: >
  Gestire stati complessi dove alcune proprietà esistono solo se altre hanno valori specifici. Le Discriminated Unions usano un 'tag' comune per discriminare tra casi. L'uso del tipo never per l'exhaustiveness checking garantisce che ogni caso sia gest
tech: "js"
tags: ["js", "typescript & advanced types"]
pdf_file: "discriminated-unions-ed-exhaustiveness-checking.pdf"
---

## Esigenza Reale
Modellare lo stato di una richiesta HTTP (Idle, Loading, Success, Error) evitando che l'app acceda ai dati quando è in errore.

## Analisi Tecnica
Problema: Accesso a proprietà inesistenti in determinati stati (es. leggere data quando loading è true) e bug logici dovuti a casi non gestiti. Perché: Uso il controllo di esaustività. Ho scelto questa tecnica per rendere illegali gli stati impossibili già a livello di compilatore.

## Esempio Implementativo

```js
* Modello gli stati di una richiesta HTTP come Discriminated Union. Il campo
* 'status' è il "discriminante": TypeScript lo usa per restringere il tipo in
* ogni branch. */
 type IdleState = 
{ status: 'idle' }
; type LoadingState = 
{ status: 'loading'; startedAt: Date }
; type SuccessState<T> = 
{ status: 'success'; data: T; fetchedAt: Date }
; type ErrorState = 
{ status: 'error'; error: Error; retriesLeft: number }
; type RequestState<T> = IdleState | LoadingState | SuccessState<T> |
ErrorState;
* Funzione di exhaustiveness checking: se tutti i casi sono coperti, 'state' ha
* tipo 'never'. Se aggiungo un nuovo stato alla Union senza aggiornare lo
* switch, TypeScript genera un errore. */
 function assertNever(state: never): never 
{ throw new Error('Stato non gestito: ' + JSON.stringify(state)); }
 
* Componente che usa il tipo corretto in ogni branch: TypeScript impedisce
* accessi illegali. */
 function renderRequestState<T>(state: RequestState<T>): string 
{ switch (state.status) 
{ case 'idle': return 'In attesa di avvio...'; case 'loading': 
// TypeScript sa che state: LoadingState: posso accedere a startedAt const
// elapsed = Date.now() - state.startedAt.getTime(); return `Caricamento in
// corso... ($
{elapsed}
ms)`; case 'success': 
// TypeScript sa che state: SuccessState<T>: posso accedere a data e fetchedAt
// return `Dati caricati alle $
{state.fetchedAt.toLocaleTimeString()}
: $
{JSON.stringify(state.data)}
`; case 'error': 
// TypeScript sa che state: ErrorState: posso accedere a error e retriesLeft
// return `Errore: $
{state.error.message}
. Tentativi rimasti: $
{state.retriesLeft}
`; default: 
// Exhaustiveness check: se tutti i casi sono coperti, state è never return
// assertNever(state);
// Errore a compile time se manca un caso }
 }
 
/* Dimostro il valore dell'exhaustiveness: aggiungo un nuovo stato. */
 type CancelledState = 
{ status: 'cancelled'; cancelledBy: string }
; type RequestStateV2<T> = RequestState<T> | CancelledState; function
renderRequestStateV2<T>(state: RequestStateV2<T>): string
{ switch (state.status) 
{ case 'idle': return 'In attesa...'; case 'loading': return `Caricamento... ($
{Date.now() - state.startedAt.getTime()}
ms)`; case 'success': return `Dati: $
{JSON.stringify(state.data)}
`; case 'error': return `Errore: $
{state.error.message}
`; 
// case 'cancelled': mancante -> TypeScript ERRORE su assertNever(state): 
// Argument of type 'CancelledState' is not assignable to parameter of type
// 'never' default: return assertNever(state);
// Compile error finché non aggiungo il case 'cancelled' }
 }
 
/* Applico il pattern a un sistema di pagamento con stati complessi: */
 type PaymentState = | 
{ status: 'draft'; amount: number; currency: string }
 | 
{ status: 'pending_authorization'; amount: number; authToken: string }
 | 
{ status: 'authorized'; amount: number; authToken: string; authorizedAt: Date }
 | 
{ status: 'captured'; amount: number; capturedAt: Date; receiptUrl: string }
 | 
{ status: 'refunded'; originalAmount: number; refundedAmount: number;
refundedAt: Date }
 | 
{ status: 'failed'; reason: string; failedAt: Date; retryable: boolean }
; function processPayment(payment: PaymentState): void 
{ switch (payment.status) 
{ case 'draft': console.log(`Bozza: €$
{payment.amount}
 $
{payment.currency}
`); break; case 'pending_authorization': console.log(`In autorizzazione con
token: $
{payment.authToken}
`); break; case 'authorized': console.log(`Autorizzato il $
{payment.authorizedAt.toISOString()}
`); break; case 'captured': console.log(`Catturato. Ricevuta: $
{payment.receiptUrl}
`); break; case 'refunded': console.log(`Rimborsato €$
{payment.refundedAmount}
 di €$
{payment.originalAmount}
`); break; case 'failed': const action = payment.retryable ? 'Riprovo' :
'Terminato'; console.log(`Fallito: $
{payment.reason}
. $
{action}
.`); break; default: assertNever(payment); 
// Compile error se aggiungo un nuovo stato senza gestirlo }
 }
```
