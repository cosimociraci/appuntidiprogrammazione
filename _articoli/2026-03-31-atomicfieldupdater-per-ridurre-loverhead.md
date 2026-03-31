---
layout: post
title: AtomicFieldUpdater per ridurre l'overhead
date: '2026-03-31 16:25:00 '
sintesi: Creare migliaia di oggetti AtomicInteger ha un costo in termini di memoria
  (overhead dell'oggetto wrapper). AtomicIntegerFieldUpdater permette di eseguire
  operazioni atomiche su un normale campo volatile di una classe. L'updater è statico
  e unico per
esigenza: Gestire milioni di nodi in una struttura dati in memoria (come un grafo
  o una cache custom) minimizzando l'occupazione di RAM.
tech: java
tags:
- java
- concurrency & multithreading
codice: '/* Confronto il costo in memoria tra le due approcci. Con AtomicInteger:
  ogni nodo ha un riferimento (8 byte) + oggetto AtomicInteger (16 byte header + 4
  byte valore = ~20 byte) = 28 byte per nodo. */ public class NodeWithAtomicInteger
  { private final AtomicInteger status = new AtomicInteger(0); // ~28 byte extra per
  nodo } /* Con AtomicIntegerFieldUpdater: il campo volatile costa solo 4 byte. L''updater
  è statico e condiviso tra TUTTE le istanze: allocato una sola volta. */ public class
  GraphNode { // Dichiaro il campo come volatile: è il requisito fondamentale per
  gli updater volatile int status = 0; // Solo 4 byte, nessun oggetto wrapper volatile
  int refCount = 0; volatile int version = 0; /* Gli updater sono statici: esistono
  una sola volta per la classe, indipendentemente da quante istanze creo. Usano reflection
  per accedere al campo: il campo deve essere visible e volatile. */ private static
  final AtomicIntegerFieldUpdater<GraphNode> STATUS_UPDATER = AtomicIntegerFieldUpdater.newUpdater(GraphNode.class,
  "status"); private static final AtomicIntegerFieldUpdater<GraphNode> REF_UPDATER
  = AtomicIntegerFieldUpdater.newUpdater(GraphNode.class, "refCount"); private static
  final AtomicIntegerFieldUpdater<GraphNode> VERSION_UPDATER = AtomicIntegerFieldUpdater.newUpdater(GraphNode.class,
  "version"); /* Eseguo il Compare-And-Set atomico: equivalente a AtomicInteger.compareAndSet()
  ma senza allocazione. */ public boolean markAsProcessed() { return STATUS_UPDATER.compareAndSet(this,
  0, 1); } public int incrementRefCount() { return REF_UPDATER.incrementAndGet(this);
  } public int getAndIncrementVersion() { return VERSION_UPDATER.getAndIncrement(this);
  } /* Verifica dello stato senza lock: la lettura di un volatile è atomica per i
  tipi <= 64 bit. */ public boolean isProcessed() { return status == 1; } } /* Calcolo
  il risparmio di memoria su 10 milioni di nodi: Con AtomicInteger: 10M * 28 byte
  = 280 MB extra Con volatile int: 10M * 4 byte = 40 MB -> risparmio di 240 MB e meno
  pressione sul GC */ /* In Spring Boot, uso questa tecnica per implementare una cache
  LRU custom in memoria con milioni di entry: */ @Component public class DenseLruCache<K,
  V> { private final Map<K, CacheEntry<V>> store = new ConcurrentHashMap<>(1_000_000);
  public static class CacheEntry<V> { volatile int hits = 0; // AtomicIntegerFieldUpdater
  invece di AtomicInteger final V value; CacheEntry(V value) { this.value = value;
  } private static final AtomicIntegerFieldUpdater<CacheEntry> HITS_UPDATER = AtomicIntegerFieldUpdater.newUpdater(CacheEntry.class,
  "hits"); public void recordHit() { HITS_UPDATER.incrementAndGet(this); } } }'
---

Problema: Eccessivo consumo di memoria dovuto all'allocazione di oggetti wrapper per ogni singola variabile atomica. Perché: Uso gli static field updaters. Ho scelto questa tecnica per mantenere l'atomicità tramite reflection interna (CAS) senza pagare il prezzo dell'allocazione di milioni di piccoli oggetti wrapper.