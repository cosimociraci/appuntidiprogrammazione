---
layout: post
title: Thread-Safety e Native State
date: '2026-03-31 16:25:01 '
sintesi: La memoria nativa non rispetta le regole di visibilità di Java. Due thread
  Java che accedono allo stesso MemorySegment possono causare data race impossibili
  da rilevare per la JVM (niente ConcurrentModificationException). La soluzione è
  usare Arena.o
esigenza: Garantire l'integrità dei dati in un database a chiave-valore in memoria
  scritto in C e usato da Java.
tech: java
tags:
- java
- jni & project panama
codice: '/* Implemento un dizionario in-memory thread-safe che usa memoria nativa
  per i valori. La chiave è in Java (String), il valore è in memoria nativa per evitare
  pressione sul GC. */ @Component public class NativeKeyValueStore { private final
  Arena sharedArena = Arena.ofShared(); private final ConcurrentHashMap<String, MemorySegment>
  index = new ConcurrentHashMap<>(); private static final VarHandle INT_VH = ValueLayout.JAVA_INT.varHandle();
  private static final VarHandle LONG_VH = ValueLayout.JAVA_LONG.varHandle(); /* Scrittura
  con semantica "release": garantisce che tutte le scritture precedenti siano visibili
  agli altri thread prima che il valore sia considerato "pubblicato". */ public void
  put(String key, int value) { MemorySegment segment = index.computeIfAbsent(key,
  k -> sharedArena.allocate(ValueLayout.JAVA_INT)); // setRelease: barriera di memoria
  in scrittura // Gli altri thread che fanno getAcquire vedranno questo valore aggiornato
  INT_VH.setRelease(segment, 0L, value); } /* Lettura con semantica "acquire": garantisce
  che il thread veda tutti i dati scritti prima del setRelease corrispondente. */
  public int get(String key) { MemorySegment segment = index.get(key); if (segment
  == null) throw new KeyNotFoundException(key); // getAcquire: barriera di memoria
  in lettura return (int) INT_VH.getAcquire(segment, 0L); } /* Per operazioni atomiche
  CAS (Compare-And-Swap) sulla memoria nativa: */ public boolean compareAndSet(String
  key, int expectedValue, int newValue) { MemorySegment segment = index.get(key);
  if (segment == null) return false; return INT_VH.compareAndSet(segment, 0L, expectedValue,
  newValue); } /* Esempio di data race da EVITARE: accesso non sincronizzato da thread
  multipli. */ @Test public void demonstrateDataRace() throws Exception { Arena sharedArena
  = Arena.ofShared(); MemorySegment counter = sharedArena.allocate(ValueLayout.JAVA_LONG);
  // SBAGLIATO: due thread incrementano il counter senza sincronizzazione ExecutorService
  exec = Executors.newFixedThreadPool(2); for (int i = 0; i < 2; i++) { exec.submit(()
  -> { for (int j = 0; j < 100_000; j++) { long current = (long) LONG_VH.get(counter,
  0L); // leggi LONG_VH.set(counter, 0L, current + 1); // scrivi: data race! } });
  } exec.shutdown(); exec.awaitTermination(5, TimeUnit.SECONDS); long result = (long)
  LONG_VH.get(counter, 0L); // Risultato atteso: 200_000, ma sarà < 200_000 a causa
  del race condition log.info("Counter finale (con race): {}", result); // CORRETTO:
  uso getAndAdd atomico long correctResult = (long) LONG_VH.getAndAdd(counter, 0L,
  1L); // CAS atomico } /* Per strutture dati più complesse, uso un lock esplicito
  + barriere di memoria: */ public void atomicUpdate(String key, int delta) { MemorySegment
  segment = index.get(key); if (segment == null) return; int current, newValue; do
  { current = (int) INT_VH.getVolatile(segment, 0L); newValue = current + delta; }
  while (!INT_VH.compareAndSet(segment, 0L, current, newValue)); // CAS loop lock-free
  }'
---

Problema: Corruzione silenziosa dei dati quando più thread Java manipolano la stessa area di memoria nativa. Perché: Uso Arena.ofShared() combinata con barriere di memoria. Ho scelto di gestire esplicitamente la sincronizzazione per assicurarmi che le scritture di un thread siano visibili agli altri prima di procedere.