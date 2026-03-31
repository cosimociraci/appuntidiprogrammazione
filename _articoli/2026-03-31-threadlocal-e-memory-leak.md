---
layout: post
title: "ThreadLocal e Memory Leak"
date: 2026-03-31 16:50:23 
sintesi: "ThreadLocal è utile per trasportare contesti (es. SecurityContext o TransactionID) senza passarli come parametri. In ambienti con thread pool (come Spring Boot), i thread non muoiono mai. Dimenticare di chiamare .remove() causa memory leak gravissimi"
tech: java
tags: ['java', 'concurrency & multithreading']
pdf_file: "threadlocal-e-memory-leak.pdf"
---

## Esigenza Reale
Passare l'ID della transazione o le informazioni sull'utente autenticato attraverso i vari layer (Service, Repository) in modo trasparente.

## Analisi Tecnica
Problema: Memory leak nei server web dovuto alla persistenza dei dati nel contesto del thread anche dopo la fine della richiesta. Perché: Uso il pattern try-finally con remove(). Ho scelto questo rigore implementativo per assicurarmi che il thread torni nel pool "pulito", evitando contaminazioni di dati tra utenti diversi.

## Esempio Implementativo

```java
/* Definisco il contenitore per il contesto dell'utente come ThreadLocal statico. Ogni thread del pool ha la sua copia indipendente del valore. */ public class UserContext { private static final ThreadLocal<UserCtx> CTX = new ThreadLocal<>(); public static void set(UserCtx ctx) { CTX.set(ctx); } public static UserCtx get() { return CTX.get(); } /* Il remove() è il punto critico: senza di esso, il thread torna nel pool di Tomcat con il vecchio UserCtx ancora dentro, contaminando la richiesta successiva di un utente diverso. */ public static void clear() { CTX.remove(); } } /* Uso corretto in un Filter Spring: imposto il contesto all'inizio della richiesta e lo pulisco SEMPRE nel finally, anche in caso di eccezione. */ @Component public class UserContextFilter implements Filter { @Override public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain) throws IOException, ServletException { HttpServletRequest httpReq = (HttpServletRequest) req; String userId = httpReq.getHeader("X-User-Id"); String traceId = httpReq.getHeader("X-Trace-Id"); UserContext.set(new UserCtx(userId, traceId)); try { chain.doFilter(req, res); } finally { UserContext.clear(); // Garantito anche in caso di eccezione: il thread torna pulito nel pool } } } /* Ora qualsiasi service o repository può leggere il contesto senza riceverlo come parametro: */ @Service public class OrderService { public List<Order> findMyOrders() { String userId = UserContext.get().getUserId(); // Disponibile ovunque nello stesso thread return orderRepository.findByUserId(userId); } } /* ATTENZIONE con i virtual thread: ogni virtual thread ha il proprio ThreadLocal, ma vengono creati e distrutti per ogni richiesta. Il memory leak non si manifesta come con i thread OS del pool, ma il costo di allocazione del ThreadLocal rimane. Per i virtual thread preferisco passare il contesto esplicitamente o usare ScopedValue (Java 21 preview): */ // ScopedValue: il successore moderno di ThreadLocal per i virtual thread ScopedValue<UserCtx> USER_CTX = ScopedValue.newInstance(); ScopedValue.where(USER_CTX, new UserCtx(userId, traceId)) .run(() -> { // Tutto il codice qui dentro ha accesso a USER_CTX.get() orderService.findMyOrders(); }); // Nessun remove() necessario: il valore è automaticamente scoped alla chiamata run() /* Rilevo i ThreadLocal leak in produzione tramite un agente di monitoraggio o ispezionando i thread con jstack: */ // jstack <pid> | grep -A 5 "http-nio" // Se vedo ThreadLocal con valori non null su thread idle, c'è un leak /* In Spring Boot, registro un interceptor che verifica che il ThreadLocal sia stato pulito al termine di ogni richiesta: */ @Component public class ThreadLocalLeakDetector implements HandlerInterceptor { @Override public void afterCompletion(HttpServletRequest req, HttpServletResponse res, Object handler, Exception ex) { if (UserContext.get() != null) { log.error("LEAK RILEVATO: UserContext non pulito per {}", req.getRequestURI()); UserContext.clear(); // Pulisco comunque per proteggere la richiesta successiva } } }
```
