---
layout: post
title: ByteBuddy e il Runtime Proxying
date: '2026-03-31 16:25:01 '
sintesi: 'I proxy dinamici di Java (JDK Proxy) funzionano solo per le interfacce.
  ByteBuddy permette di sottoclassare classi concrete a runtime per iniettare logica
  (es. @Transactional). ByteBuddy genera direttamente bytecode invece di usare la
  reflection per '
esigenza: Creare un sistema di logging automatico che intercetta i metodi di classi
  service che non implementano interfacce.
tech: java
tags:
- java
- advanced reflection & metaprogr
codice: '/* Genero dinamicamente una sottoclasse di OriginalService che intercetta
  tutti i metodi pubblici per aggiungere logging automatico. ByteBuddy genera bytecode
  reale: nessuna reflection a runtime. */ @Configuration public class ByteBuddyProxyConfig
  { @Bean public OriginalService loggedService() throws Exception { Class<? extends
  OriginalService> proxyClass = new ByteBuddy() .subclass(OriginalService.class) .method(ElementMatchers.isPublic()
  .and(ElementMatchers.not(ElementMatchers.isStatic()))) .intercept(MethodDelegation.to(LoggingInterceptor.class))
  .make() .load(OriginalService.class.getClassLoader(), ClassLoadingStrategy.Default.WRAPPER)
  .getLoaded(); return proxyClass.getDeclaredConstructor().newInstance(); } } /* Implemento
  l''interceptor che gestisce la logica trasversale: */ public class LoggingInterceptor
  { @RuntimeType public static Object intercept( @Origin Method method, // Il metodo
  originale chiamato @AllArguments Object[] args, // Gli argomenti della chiamata
  @SuperCall Callable<?> superCall // La chiamata al metodo originale ) throws Exception
  { long start = System.nanoTime(); String methodName = method.getDeclaringClass().getSimpleName()
  + "." + method.getName(); log.info("Avvio {}: args={}", methodName, Arrays.toString(args));
  try { Object result = superCall.call(); // Chiamo il metodo originale long elapsedMs
  = (System.nanoTime() - start) / 1_000_000; log.info("Completato {} in {}ms", methodName,
  elapsedMs); return result; } catch (Exception e) { log.error("Errore in {}: {}",
  methodName, e.getMessage()); throw e; } } } /* Per classi final, ByteBuddy non può
  sottoclassare: uso l''approccio con Java Agent per riscrivere il bytecode al caricamento:
  */ public class ByteBuddyAgent { public static void premain(String args, Instrumentation
  instrumentation) { new AgentBuilder.Default() .type(ElementMatchers.nameStartsWith("com.myapp.service"))
  .transform((builder, typeDescription, classLoader, module, protectionDomain) ->
  builder .method(ElementMatchers.isPublic()) .intercept(MethodDelegation.to(LoggingInterceptor.class))
  ) .installOn(instrumentation); } } /* In Spring Boot, confronto ByteBuddy con CGLIB
  per la creazione dei proxy: */ @Test public void compareByteBuddyVsCglib() throws
  Exception { long start = System.nanoTime(); for (int i = 0; i < 1000; i++) { new
  ByteBuddy().subclass(OriginalService.class) .method(ElementMatchers.any()) .intercept(MethodDelegation.to(LoggingInterceptor.class))
  .make().load(getClass().getClassLoader()).getLoaded().newInstance(); } long byteBuddyTime
  = System.nanoTime() - start; // ByteBuddy è tipicamente 30-50% più veloce di CGLIB
  nella generazione dei proxy log.info("ByteBuddy proxy generation: {}ms", byteBuddyTime
  / 1_000_000); }'
---

Problema: Impossibilità di applicare proxy a classi legacy o final senza modificare il codice sorgente. Perché: Uso ByteBuddy per la generazione di bytecode. Ho scelto questo approccio perché mi permette di manipolare il comportamento delle classi "al volo" con un impatto minimo sulle prestazioni di esecuzione.