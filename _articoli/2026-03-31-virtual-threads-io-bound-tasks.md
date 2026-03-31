---
layout: post
title: Virtual Threads & I/O Bound Tasks
date: '2026-03-31 16:25:00 '
sintesi: 'Con Java 21, i Virtual Threads cambiano il paradigma: non dobbiamo più preoccuparci
  di saturare il pool di thread dell''OS. Per task bloccanti (chiamate HTTP, JDBC),
  non serve più usare complessi approcci reattivi. I Virtual Threads sono leggeri
  e ges'
esigenza: Scalare un gateway API che effettua chiamate sincrone a servizi esterni
  senza esaurire i thread del server Tomcat.
tech: java
tags:
- java
- concurrency & multithreading
codice: '/* Configuro un executor che crea un virtual thread per ogni richiesta. I
  virtual thread sono smontati dal carrier thread durante le operazioni bloccanti
  (I/O, sleep, JDBC) e rimontati quando sono pronti: zero spreco di thread OS. */
  try (var executor = Executors.newVirtualThreadPerTaskExecutor()) { List<Future<String>>
  futures = IntStream.range(0, 10_000) .mapToObj(i -> executor.submit(() -> { // Questa
  sleep non blocca nessun thread OS: il virtual thread viene "parcheggiato" Thread.sleep(Duration.ofMillis(500));
  return fetchFromExternalService(i); // Chiamata HTTP bloccante, gestita dalla JVM
  })) .toList(); for (Future<String> f : futures) { System.out.println(f.get()); }
  } /* Configurazione in Spring Boot 3.2+: abilito i virtual thread per Tomcat in
  application.properties. spring.threads.virtual.enabled=true Questo fa sì che ogni
  richiesta HTTP venga gestita su un virtual thread invece che su un thread del pool
  Tomcat. */ /* Per JDBC con HikariCP, i virtual thread funzionano bene perché il
  pool di connessioni è già il collo di bottiglia reale: il virtual thread aspetta
  una connessione disponibile senza bloccare thread OS. */ @Service public class GatewayService
  { private final RestClient restClient; public GatewayService(RestClient.Builder
  builder) { // RestClient è sincrono ma va benissimo con i virtual thread this.restClient
  = builder.baseUrl("https://api.external.com").build(); } public String callExternalService(String
  id) { // Questa chiamata bloccante non satura più il pool Tomcat return restClient.get().uri("/resource/{id}",
  id) .retrieve().body(String.class); } } /* PINNING: il caso da evitare. Se uso synchronized
  attorno a operazioni I/O, il virtual thread rimane "pinned" al carrier thread OS,
  annullando il vantaggio. */ // SBAGLIATO: synchronized blocca il carrier thread
  durante l''I/O public synchronized String badMethod() { return restClient.get().uri("/slow").retrieve().body(String.class);
  } // CORRETTO: uso ReentrantLock che supporta il parking dei virtual thread private
  final ReentrantLock vtLock = new ReentrantLock(); public String goodMethod() { vtLock.lock();
  try { return restClient.get().uri("/slow").retrieve().body(String.class); } finally
  { vtLock.unlock(); } }'
---

Problema: Ogni thread dell'OS occupa circa 1MB di memoria; con migliaia di connessioni concorrenti, il server va in OutOfMemoryError. Perché: Uso Executors.newVirtualThreadPerTaskExecutor(). Ho deciso di delegare alla JVM lo scheduling, permettendo di gestire milioni di thread con un footprint minimo di memoria.