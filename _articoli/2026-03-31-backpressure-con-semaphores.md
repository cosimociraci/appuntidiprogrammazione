---
layout: post
title: "Backpressure con Semaphores"
date: 2026-03-31 19:21:08 
sintesi: "In sistemi asincroni, è facile che un produttore veloce inondi un consumatore lento, esaurendo la memoria (unbounded queue). L'uso di Semaphore come meccanismo di backpressure è semplice ma efficace. Il produttore deve acquisire un permesso prima di "
tech: java
tags: [java, "concurrency & multithreading"]
pdf_file: "backpressure-con-semaphores.pdf"
---

## Esigenza Reale
Proteggere un servizio di invio email che non può gestire più di 50 richieste concorrenti verso il provider SMTP.

## Analisi Tecnica
Problema: Rischio di crash dell'applicazione dovuto a un accumulo infinito di task nella coda della memoria. Perché: Uso un Semaphore. Ho scelto questa via per implementare un limite fisico immediato: se non c'è capacità, il thread chiamante aspetta, applicando pressione inversa naturale lungo la catena di chiamata.

## Esempio Implementativo

```java
/* Limito la concorrenza a 50 task attivi contemporaneamente. Il Semaphore funge
* da valvola: quando tutti i 50 permessi sono occupati, il produttore si blocca
* naturalmente invece di continuare ad accodare. */ @Service public class
* EmailDispatchService { private static final int MAX_CONCURRENT = 50; private
* final Semaphore semaphore = new Semaphore(MAX_CONCURRENT, true); // fair=true:
* FIFO tra i thread in attesa private final ExecutorService executor =
* Executors.newCachedThreadPool(); public void sendEmail(EmailRequest request)
* throws InterruptedException { semaphore.acquire(); // Mi fermo qui se tutti i
* 50 slot sono occupati try { executor.submit(() -> { try {
* smtpClient.send(request); // Operazione bloccante verso il provider } catch
* (Exception e) { log.error("Errore invio email a {}", request.getTo(), e); }
* finally { semaphore.release(); // Libero il posto per il prossimo task } }); }
* catch (RejectedExecutionException e) { semaphore.release(); // Rilascio il
* permesso se l'executor ha rifiutato il task throw new
* ServiceUnavailableException("Executor non disponibile"); } } /* Versione non
* bloccante con tryAcquire: restituisce subito false invece di aspettare. Utile
* per rispondere immediatamente con HTTP 429 invece di bloccare il thread
* chiamante. */ public boolean trySendEmail(EmailRequest request) { if
* (!semaphore.tryAcquire()) { log.warn("Backpressure attiva: {} richieste in
* corso, richiesta scartata", MAX_CONCURRENT); return false; // Il chiamante
* gestirà il rifiuto } executor.submit(() -> { try { smtpClient.send(request); }
* finally { semaphore.release(); } }); return true; } /* Espongo le metriche del
* semaphore tramite Micrometer per monitorare la saturazione in produzione: */
* @Bean public MeterBinder semaphoreMetrics() { return registry -> {
* Gauge.builder("email.semaphore.available_permits", semaphore,
* Semaphore::availablePermits) .description("Permessi disponibili nel semaphore
* email") .register(registry); Gauge.builder("email.semaphore.queue_length",
* semaphore, Semaphore::getQueueLength) .description("Thread in attesa di un
* permesso") .register(registry); }; } }
```
