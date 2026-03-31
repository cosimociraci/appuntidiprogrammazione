---
layout: post
title: CompletableFuture per Pipeline Reattive
date: '2026-03-31 16:25:00 '
sintesi: 'Gestire callback annidate (callback hell) rende il codice multithread illeggibile.
  CompletableFuture permette di costruire pipeline funzionali: "fai questo, poi quello,
  se fallisce gestisci così". Il vantaggio tecnico è la possibilità di comporre ris'
esigenza: Comporre un profilo utente aggregando dati provenienti da tre diversi microservizi
  (Ordini, Preferenze, Anagrafica) in parallelo.
tech: java
tags:
- java
- concurrency & multithreading
codice: '/* Definisco un executor dedicato per le chiamate I/O asincrone. Non uso
  il ForkJoinPool comune perché è pensato per task CPU-bound e potrei saturarlo con
  operazioni bloccanti. */ private final ExecutorService ioExecutor = Executors.newVirtualThreadPerTaskExecutor();
  /* Avvio i tre recuperi in parallelo senza bloccare il thread chiamante. Ogni supplyAsync
  parte immediatamente su un virtual thread dell''ioExecutor. */ public CompletableFuture<UserProfile>
  buildUserProfile(String userId) { CompletableFuture<UserData> userFuture = CompletableFuture.supplyAsync(
  () -> userService.fetchUser(userId), ioExecutor ); CompletableFuture<List<Order>>
  ordersFuture = CompletableFuture.supplyAsync( () -> orderService.fetchOrders(userId),
  ioExecutor ); CompletableFuture<Preferences> prefsFuture = CompletableFuture.supplyAsync(
  () -> prefsService.fetchPreferences(userId), ioExecutor ); /* Aspetto che tutti
  e tre siano completati, poi combino i risultati. allOf non restituisce valori: serve
  join() su ciascun future dopo. */ return CompletableFuture.allOf(userFuture, ordersFuture,
  prefsFuture) .thenApply(ignored -> { UserData user = userFuture.join(); List<Order>
  orders = ordersFuture.join(); Preferences prefs = prefsFuture.join(); return new
  UserProfile(user, orders, prefs); }) .exceptionally(ex -> { // Gestione centralizzata
  degli errori di qualsiasi step della pipeline log.error("Errore nella costruzione
  del profilo per userId={}", userId, ex); return UserProfile.empty(userId); }); }
  /* Aggiungo un timeout globale per non lasciare il client in attesa infinita se
  un microservizio è lento: */ public UserProfile buildUserProfileWithTimeout(String
  userId) { try { return buildUserProfile(userId) .orTimeout(3, TimeUnit.SECONDS)
  .exceptionally(ex -> { if (ex instanceof TimeoutException) { log.warn("Timeout nella
  costruzione del profilo per userId={}", userId); } return UserProfile.empty(userId);
  }) .get(); } catch (InterruptedException | ExecutionException e) { Thread.currentThread().interrupt();
  return UserProfile.empty(userId); } } /* In Spring Boot, espongo il metodo come
  endpoint REST che restituisce il profilo in modo non bloccante. Con virtual thread
  abilitati, il thread HTTP aspetta senza occupare thread OS: */ @RestController @RequiredArgsConstructor
  public class ProfileController { private final ProfileService profileService; @GetMapping("/profile/{userId}")
  public UserProfile getProfile(@PathVariable String userId) { // Con virtual thread,
  questa get() non blocca thread OS return profileService.buildUserProfileWithTimeout(userId);
  } } /* Per comporre pipeline sequenziali (output di uno è input del successivo):
  */ CompletableFuture<String> pipeline = CompletableFuture .supplyAsync(() -> fetchRawData(userId),
  ioExecutor) .thenApplyAsync(raw -> enrichData(raw), ioExecutor) .thenApplyAsync(enriched
  -> formatForResponse(enriched), ioExecutor) .exceptionally(ex -> "fallback-data");'
---

Problema: Codice asincrono difficile da mantenere, debuggare e testare a causa di logiche di sincronizzazione manuali. Perché: Uso l'API fluent di CompletableFuture. Ho scelto questo approccio per rendere esplicita la sequenza delle operazioni e gestire le eccezioni in modo centralizzato lungo tutta la catena.