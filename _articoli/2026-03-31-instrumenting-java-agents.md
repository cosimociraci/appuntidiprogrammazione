---
layout: post
title: "Instrumenting Java Agents"
date: 2026-03-31 17:02:46 
sintesi: "I Java Agent, tramite l'API Instrumentation, possono intercettare il caricamento di ogni classe e modificarne il bytecode prima che venga eseguito. Questa è la tecnica usata dai tool di monitoraggio APM (NewRelic, Dynatrace) per iniettare sonde di te"
tech: java
tags: ['java', 'advanced reflection & metaprogr']
pdf_file: "instrumenting-java-agents.pdf"
---

## Esigenza Reale
Aggiungere metriche di performance a una vecchia applicazione legacy senza toccare un solo file del codice sorgente.

## Analisi Tecnica
Problema: Necessità di monitorare o modificare il comportamento di un'applicazione blindata o di terze parti. Perché: Sviluppo un Java Agent. Ho scelto questa tecnica perché agisce a livello di JVM, permettendomi di "riscrivere" le classi mentre vengono caricate in memoria in modo totalmente trasparente all'app.

## Esempio Implementativo

```java
/* Struttura del progetto agent: deve produrre un JAR con il MANIFEST.MF che dichiara il punto di ingresso. */ // MANIFEST.MF: // Premain-Class: com.myagent.TimingAgent // Agent-Class: com.myagent.TimingAgent // Can-Redefine-Classes: true // Can-Retransform-Classes: true /* Definisco il punto di ingresso dell'agente. premain viene invocato prima del main dell'applicazione target. */ public class TimingAgent { private static final MeterRegistry registry = new SimpleMeterRegistry(); public static void premain(String agentArgs, Instrumentation instrumentation) { log.info("TimingAgent avviato con args: {}", agentArgs); // Uso ByteBuddy tramite AgentBuilder per trasformare le classi al caricamento new AgentBuilder.Default() // Intercetto tutte le classi nel package specificato negli args .type(ElementMatchers.nameStartsWith(agentArgs != null ? agentArgs : "com.")) .transform((builder, typeDescription, classLoader, module, protectionDomain) -> builder .method(ElementMatchers.isPublic() .and(ElementMatchers.not(ElementMatchers.isConstructor())) .and(ElementMatchers.not(ElementMatchers.isStatic()))) .intercept(MethodDelegation.to(TimingInterceptor.class)) ) .with(AgentBuilder.Listener.StreamWriting.toSystemError()) // Log degli errori di trasformazione .installOn(instrumentation); } /* agentmain viene invocato quando l'agente viene allegato a una JVM già in esecuzione (attach API). */ public static void agentmain(String agentArgs, Instrumentation instrumentation) { premain(agentArgs, instrumentation); // Stessa logica: può essere usato sia a startup che a runtime } } /* Implemento l'interceptor che misura il tempo di ogni metodo: */ public class TimingInterceptor { @RuntimeType public static Object intercept( @Origin Method method, @AllArguments Object[] args, @SuperCall Callable<?> superMethod ) throws Exception { String metricName = method.getDeclaringClass().getSimpleName() + "." + method.getName(); Timer.Sample sample = Timer.start(); try { return superMethod.call(); } catch (Exception e) { Counter.builder(metricName + ".errors").register(TimingAgent.registry).increment(); throw e; } finally { sample.stop(Timer.builder(metricName + ".duration") .description("Durata metodo " + metricName) .register(TimingAgent.registry)); } } } /* Creo il JAR dell'agente con Maven Shade Plugin e lo allego all'applicazione target: */ // java -javaagent:timing-agent.jar=com.myapp.service -jar target-app.jar /* Per allegare l'agente a una JVM già in esecuzione (attach dinamico, senza riavvio): */ public class AgentAttacher { public static void attachToRunningJvm(String pid, String agentJarPath) throws Exception { VirtualMachine vm = VirtualMachine.attach(pid); try { vm.loadAgent(agentJarPath, "com.myapp.service"); log.info("Agent allegato alla JVM PID {} con successo", pid); } finally { vm.detach(); } } } /* In Spring Boot, espongo le metriche raccolte dall'agente tramite Actuator: */ @Bean public MeterRegistryCustomizer<MeterRegistry> agentMetricsExporter() { return registry -> TimingAgent.getRegistry().getMeters() .forEach(meter -> registry.register(meter)); }
```
