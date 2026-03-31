---
layout: post
title: "MethodHandle vs Reflection"
date: 2026-03-31 17:02:46 
sintesi: "L'API java.lang.reflect.Method è lenta perché esegue controlli di accesso a ogni chiamata e non viene facilmente "inlineata" dal compilatore JIT. MethodHandle (introdotto in Java 7) agisce come un puntatore a funzione tipizzato e costante. Se memoriz"
tech: java
tags: ['java', 'advanced reflection & metaprogr']
pdf_file: "methodhandle-vs-reflection.pdf"
---

## Esigenza Reale
Creare un dispatcher di eventi ultra-veloce che invoca metodi di plugin caricati a runtime in base al tipo di messaggio.

## Analisi Tecnica
Problema: L'invocazione tramite Reflection classica introduce un overhead misurabile che scala male all'aumentare delle chiamate. Perché: Uso MethodHandle. Ho scelto questa via perché, una volta risolto il puntatore (lookup), l'esecuzione è estremamente vicina alla velocità nativa grazie alla capacità della JVM di ottimizzare il call site.

## Esempio Implementativo

```java
/* Risolvo i MethodHandle una sola volta in un blocco static: il costo del lookup avviene allo startup, non a ogni chiamata. Nei campi static final il JIT può inlineare la chiamata come se fosse diretta. */ private static final MethodHandle PROCESS_HANDLE; private static final MethodHandle VALIDATE_HANDLE; static { try { MethodHandles.Lookup lookup = MethodHandles.lookup(); PROCESS_HANDLE = lookup.findVirtual( MessageService.class, "process", MethodType.methodType(void.class, String.class)); VALIDATE_HANDLE = lookup.findVirtual( MessageService.class, "validate", MethodType.methodType(boolean.class, String.class)); } catch (NoSuchMethodException | IllegalAccessException e) { throw new ExceptionInInitializerError(e); } } /* Confronto le performance con JMH per quantificare il guadagno: */ @Benchmark public void withReflection(BenchState state) throws Exception { state.method.invoke(state.service, "payload"); // Controllo accesso ad ogni chiamata } @Benchmark public void withMethodHandle(BenchState state) throws Throwable { PROCESS_HANDLE.invokeExact(state.service, "payload"); // JIT può inlineare questo } // Risultato tipico: MethodHandle è 3-10x più veloce di reflection su call site caldi /* Implemento un dispatcher di eventi basato su MethodHandle per un sistema di plugin: */ @Component public class EventDispatcher { // Mappa tipo evento -> MethodHandle del metodo handler: risolta allo startup private final Map<Class<?>, MethodHandle> handlerMap = new ConcurrentHashMap<>(); public void registerHandler(Object handler) throws Exception { MethodHandles.Lookup lookup = MethodHandles.lookup(); for (Method method : handler.getClass().getDeclaredMethods()) { if (method.isAnnotationPresent(EventHandler.class)) { Class<?> eventType = method.getParameterTypes()[0]; MethodHandle mh = lookup.unreflect(method).bindTo(handler); // bindTo: lego l'istanza al handle per evitare di passarla ad ogni chiamata handlerMap.put(eventType, mh); } } } public void dispatch(Object event) throws Throwable { MethodHandle handler = handlerMap.get(event.getClass()); if (handler != null) { handler.invoke(event); // Chiamata quasi nativa: JIT ottimizza il call site } } } /* In Spring Boot, registro i plugin al momento dell'avvio e uso il dispatcher nelle richieste: */ @EventListener(ApplicationReadyEvent.class) public void registerPlugins() throws Exception { for (Object plugin : pluginRegistry.getAll()) { dispatcher.registerHandler(plugin); } }
```
