---
layout: post
title: "Metaspace e ClassLoader Leaks"
date: 2026-04-03 14:39:36
sintesi: "Il Metaspace contiene i metadati delle classi. Caricare dinamicamente classi (es. tramite proxy o script) senza un limite pu saturare la memoria fisica del server. Se il Metaspace cresce all'infinito, significa che i ClassLoader non vengono scaricat"
tech: "java"
tags: ["java", "jvm tuning & garbage collection"]
pdf_file: "metaspace-e-classloader-leaks.pdf"
---

## Esigenza Reale
Diagnosticare memory leak in applicazioni che usano pesantemente Reflection, Groovy o framework di plugin dinamici.

## Analisi Tecnica
Problema: Crescita incontrollata della memoria non-heap (Metaspace) che porta all'esaurimento della RAM del server. Perché: Imposto un tetto massimo al Metaspace. Ho scelto di rendere esplicito l'errore OutOfMemoryError: Metaspace per identificare bug nei ClassLoader invece di lasciare che il processo venga ucciso dall'OS senza spiegazioni.

## Esempio Implementativo

```java
* Limito il Metaspace e abilito il logging per intercettare la crescita anomala
* prima che diventi critica. */
 java -XX:MaxMetaspaceSize=512M \ -XX:MetaspaceSize=128M \
-Xlog:class+unload=info:file=classunload.log:time \ -jar dynamic-app.jar
* MetaspaceSize=128M imposta la soglia iniziale oltre la quale G1 tenta la
* pulizia dei ClassLoader. Senza questo, il GC aspetta troppo a lungo prima di
* intervenire. */
 
/* Individuo il leak monitorando la crescita del Metaspace nel tempo: */
 @Scheduled(fixedDelay = 30_000) public void monitorMetaspace() 
{ for (MemoryPoolMXBean pool : ManagementFactory.getMemoryPoolMXBeans()) 
{ if (pool.getName().contains("Metaspace")) 
{ long used = pool.getUsage().getUsed(); long max = pool.getUsage().getMax();
double pct = max > 0 ? 100.0 * used / max : 0; log.info("Metaspace:
{}
MB / 
{}
MB (
{}
%)", used / 1_048_576, max / 1_048_576, String.format("%.1f", pct)); if (pct >
80)
{ alertService.sendWarning("Metaspace all'80%: possibile ClassLoader leak"); }
 }
 }
 }
 
* Identifico i ClassLoader che non vengono scaricati tramite heap dump e analisi
* con Eclipse MAT: */
 
// jcmd <PID> GC.heap_dump filename=heap.hprof 
// In MAT: Leak Suspects > "One instance of ClassLoader holds N classes" 
* La causa più comune in Spring Boot è la creazione ripetuta di
* ApplicationContext in test o l'uso di Groovy/scripting che compila nuove
* classi a runtime senza liberare il ClassLoader precedente: */
 
// SBAGLIATO: creo un nuovo ClassLoader a ogni richiesta senza mai rilasciarlo
// public Object executeScript(String groovyCode)
{ GroovyClassLoader loader = new GroovyClassLoader(); 
// Leak! Mai chiuso Class<?> clazz = loader.parseClass(groovyCode); return
// clazz.getDeclaredConstructor().newInstance(); }
 
// CORRETTO: riuso un ClassLoader con cache e lo chiudo esplicitamente
// @Component public class GroovyScriptExecutor implements Closeable
{ private final GroovyClassLoader sharedLoader = new GroovyClassLoader();
private final Map<String, Class<?>> scriptCache = new ConcurrentHashMap<>();
public Object execute(String scriptKey, String groovyCode) throws Exception
{ Class<?> clazz = scriptCache.computeIfAbsent(scriptKey, k ->
sharedLoader.parseClass(groovyCode)); return
clazz.getDeclaredConstructor().newInstance(); }
 @Override public void close() throws IOException 
{ sharedLoader.close(); 
// Libera tutti i ClassLoader figli e i metadati associati }
 }
```
