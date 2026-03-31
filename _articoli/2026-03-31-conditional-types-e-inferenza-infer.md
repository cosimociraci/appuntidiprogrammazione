---
layout: post
title: "Conditional Types e Inferenza (infer)"
date: 2026-03-31 17:04:41 
sintesi: "Creare utility types che si adattano dinamicamente alla struttura dei dati. La sintassi T extends U ? X : Y permette di creare logiche decisionali a livello di tipo. La keyword infer, usata all'interno di un conditional type, permette di "estrarre" u"
tech: js
tags: ['js', 'typescript & advanced types']
pdf_file: "conditional-types-e-inferenza-infer.pdf"
---

## Esigenza Reale
Estrarre automaticamente il tipo dei dati contenuti in una risposta API complessa senza doverlo ridefinire manualmente.

## Analisi Tecnica
Problema: Duplicazione di codice e disallineamento tra le definizioni delle funzioni e i tipi dei loro risultati. Perché: Uso l'inferenza condizionale. Ho scelto infer per "scoperchiare" i tipi generici e recuperare informazioni strutturali che altrimenti andrebbero perse o richiederebbero cast manuali insicuri.

## Esempio Implementativo

```js
/* Utility fondamentali basate su infer: estraggo tipi da strutture complesse senza ridefinirli. */ // Estrae il tipo contenuto in una Promise (ricorsivamente per Promise annidate) type UnpackPromise<T> = T extends Promise<infer U> ? UnpackPromise<U> : T; // Estrae il tipo di ritorno di una funzione (equivalente a ReturnType<T> della stdlib) type MyReturnType<T> = T extends (...args: any[]) => infer R ? R : never; // Estrae il tipo del primo parametro di una funzione type FirstParam<T> = T extends (first: infer P, ...rest: any[]) => any ? P : never; // Estrae il tipo degli elementi di un array type ArrayElement<T> = T extends (infer E)[] ? E : never; // Estrae il tipo del valore di una Map type MapValue<T> = T extends Map<any, infer V> ? V : never; /* Applico le utility a un'API reale per eliminare la duplicazione di tipi. */ // Definisco le funzioni API una sola volta async function fetchUser(id: number): Promise<{ id: number; name: string; email: string }> { const res = await fetch(`/api/users/${id}`); return res.json(); } async function fetchOrders(userId: number): Promise<{ orderId: string; total: number; items: string[] }[]> { const res = await fetch(`/api/users/${userId}/orders`); return res.json(); } // Estraggo i tipi di ritorno SENZA ridefinirli: fonte unica di verità type User = UnpackPromise<ReturnType<typeof fetchUser>>; // { id: number; name: string; email: string } type Order = ArrayElement<UnpackPromise<ReturnType<typeof fetchOrders>>>; // { orderId: string; total: number; items: string[] } // Se la firma di fetchUser cambia, User si aggiorna automaticamente: zero disallineamenti /* Utility avanzata: estraggo i tipi dei parametri di una funzione per creare wrapper tipizzati. */ type Parameters<T extends (...args: any[]) => any> = T extends (...args: infer P) => any ? P : never; // Creo un wrapper con retry automatico che preserva la firma originale function withRetry<T extends (...args: any[]) => Promise<any>>( fn: T, maxRetries: number = 3 ): (...args: Parameters<T>) => ReturnType<T> { return async (...args: Parameters<T>) => { let lastError: Error; for (let attempt = 0; attempt <= maxRetries; attempt++) { try { return await fn(...args); } catch (err) { lastError = err as Error; if (attempt < maxRetries) await sleep(Math.pow(2, attempt) * 100); } } throw lastError!; }; } // fetchUserWithRetry ha esattamente la stessa firma di fetchUser: type-safe al 100% const fetchUserWithRetry = withRetry(fetchUser, 3); const user = await fetchUserWithRetry(42); // user: { id: number; name: string; email: string } /* Conditional type per discriminare tra tipi sincroni e asincroni: */ type Awaited<T> = T extends PromiseLike<infer U> ? Awaited<U> : T; type IsAsync<T> = T extends (...args: any[]) => Promise<any> ? true : false; type SyncVersion<T extends (...args: any[]) => any> = IsAsync<T> extends true ? (...args: Parameters<T>) => Awaited<ReturnType<T>> : T;
```
