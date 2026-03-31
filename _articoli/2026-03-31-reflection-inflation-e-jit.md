---
layout: post
title: "Reflection Inflation e JIT"
date: 2026-03-31 19:00:07 
sintesi: "La JVM ha un'ottimizzazione interna: per le prime 15 chiamate a un metodo via reflection, usa il codice nativo (lento), poi genera una classe bytecode dedicata (veloce). Questo processo si chiama Inflation. Non bisogna preoccuparsi troppo della lente"
tech: java
tags: [java, "advanced reflection & metaprogr"]
pdf_file: "reflection-inflation-e-jit.pdf"
---

## Esigenza Reale
Comprendere perché le performance di un modulo di importazione dati migliorano improvvisamente dopo i primi secondi di esecuzione.

## Analisi Tecnica
Problema: Comportamento prestazionale incostante (jitter) durante le prime invocazioni dinamiche del sistema. Perché: Conosco il meccanismo di Inflation. Ho scelto di lasciare che la JVM gestisca la transizione automatica, ma monitoro il numero di classi generate per evitare un consumo eccessivo di Metaspace.

## Esempio Implementativo

```java
/* Regolo la soglia dopo la quale la reflection viene "gonfiata" in bytecode generato. Il default è 15: dopo 15 invocazioni, la JVM genera una classe accessor dedicata. */
// java -Dsun.reflect.inflationThreshold=5 -jar app.jar // Con threshold=5, la JVM genera il bytecode ottimizzato prima, riducendo il jitter iniziale /* Visualizzo il comportamento della Inflation con un benchmark JMH che misura il jitter delle prime invocazioni: */ @State(Scope.Thread) public class ReflectionInflationBenchmark { private Method method; private Object instance; @Setup public void setup() throws Exception { instance = new MyService(); method = MyService.class.getMethod("process", String.class); } @Benchmark @BenchmarkMode(Mode.SingleShotTime) // Misuro ogni singola invocazione @Fork(value = 1, warmups = 0) // Nessun warmup: voglio vedere le prime invocazioni fredde public Object firstInvocations() throws Exception { return method.invoke(instance, "payload"); // Le prime 15 usano codice nativo, poi scatta l'inflation } } /* Monitoro le classi accessor generate dalla Inflation per evitare che saturino il Metaspace: */ @Scheduled(fixedDelay = 30_000) public void monitorReflectionClasses() { ClassLoadingMXBean classBean = ManagementFactory.getClassLoadingMXBean(); long totalLoaded = classBean.getTotalLoadedClassCount(); // Le classi generate dalla Inflation hanno nomi come "sun.reflect.GeneratedMethodAccessor123" long generatedAccessors = Thread.getAllStackTraces().keySet().stream() .flatMap(t -> Arrays.stream(t.getStackTrace())) .filter(frame -> frame.getClassName().startsWith("sun.reflect.GeneratedMethodAccessor") || frame.getClassName().startsWith("jdk.internal.reflect.GeneratedMethodAccessor")) .map(StackTraceElement::getClassName) .distinct() .count(); log.info("Classi totali caricate: {}, Accessor generati attivi: {}", totalLoaded, generatedAccessors); if (generatedAccessors > 1000) { log.warn("Troppi accessor reflection generati: possibile leak di ClassLoader o abuso di reflection"); } } /* In Java 17+, il meccanismo di Inflation è cambiato: usa MethodHandle internamente invece di generare classi. Verifico quale meccanismo è attivo: */ @Test public void verifyInflationMechanism() throws Exception { Method method = MyService.class.getMethod("process", String.class); Object instance = new MyService(); // Invoco 20 volte per attraversare la soglia di Inflation per (int i = 0; i < 20; i++) { method.invoke(instance, "test"); } // Dopo la soglia, la reflection usa bytecode generato o MethodHandle: // in entrambi i casi le performance sono paragonabili a MethodHandle diretto long start = System.nanoTime(); for (int i = 0; i < 100_000; i++) { method.invoke(instance, "test"); } long avgNs = (System.nanoTime() - start) / 100_000; log.info("Invocazione media post-inflation: {}ns (atteso < 200ns)", avgNs); assertTrue(avgNs < 500, "Reflection ancora lenta dopo inflation: " + avgNs + "ns"); } /* Strategia consigliata per sistemi con chiamate reflection rare ma critiche: */ // 1. Se le chiamate sono < 15 totali: usare MethodHandle direttamente (nessuna inflation) // 2. Se le chiamate sono frequenti: lasciare che la JVM gestisca la transizione // 3. Se il jitter delle prime chiamate è inaccettabile: abbassare inflationThreshold a 0 // java -Dsun.reflect.inflationThreshold=0 // Genera bytecode immediamente, senza passare per il codice nativo // 4. Per Java 17+: preferire MethodHandle o VarHandle che bypassano completamente la Inflation

```
