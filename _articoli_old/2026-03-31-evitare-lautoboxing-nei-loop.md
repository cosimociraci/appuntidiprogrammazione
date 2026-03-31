---
layout: post
title: "Evitare l'Autoboxing nei Loop"
date: 2026-03-31 10:11:47 +0200
sintesi: "Java converte automaticamente i tipi primitivi (int) nei loro wrapper (Integer). All'interno di un loop critico, questo causa l'allocazione di milioni..."
tech: java
tags: ['java', 'memory & performance']
---
## Esigenza Reale
Elaborare statistiche in tempo reale su milioni di rilevazioni numeriche provenienti da sensori IoT.

## Analisi Tecnica
Problema: Degradazione delle performance e pressione sul GC causata dalla creazione silenziosa di oggetti wrapper durante i calcoli. Perché: Uso IntStream e array nativi. Ho scelto di mantenere i dati nel loro formato primitivo per sfruttare la velocità della CPU ed evitare il passaggio continuo tra stack e heap.

## Esempio Implementativo

```java
/* Confronto i tre approcci per quantificare la differenza. */ // APPROCCIO 1 - PEGGIORE: List<Integer> causa autoboxing per ogni elemento List<Integer> sensorData = new ArrayList<>(); sensorData.add(42); // Boxing: new Integer(42) allocato sull'heap int total = sensorData.stream() .filter(v -> v > 0) // Unboxing + boxing ad ogni operazione .mapToInt(Integer::intValue) // Unboxing finale .sum(); // APPROCCIO 2 - CORRETTO: array di primitivi + IntStream int[] rawSensorData = fetchRawData(); // Array di int: contiguo in memoria, zero boxing int total2 = IntStream.of(rawSensorData) .filter(v -> v > 0) // Lavora su int primitivi: nessuna allocazione .sum(); // APPROCCIO 3 - MIGLIORE per strutture dati mutabili: Eclipse Collections MutableIntList primitiveList = IntLists.mutable.empty(); primitiveList.add(42); // Nessun boxing: lista di int nativi int total3 = primitiveList.select(v -> v > 0).sum(); /* Misuro la differenza con JMH per renderla oggettiva: */ @State(Scope.Benchmark) public class AutoboxingBenchmark { int[] primitiveData = IntStream.range(0, 1_000_000).toArray(); List<Integer> boxedData = IntStream.range(0, 1_000_000).boxed().collect(Collectors.toList()); @Benchmark public int withBoxing() { return boxedData.stream().mapToInt(Integer::intValue).filter(v -> v > 0).sum(); } @Benchmark public int withoutBoxing() { return IntStream.of(primitiveData).filter(v -> v > 0).sum(); } // Risultato atteso: withoutBoxing è 3-5x più veloce e alloca zero oggetti } /* In Spring Boot, il layer di aggregazione dei dati IoT usa esclusivamente primitive: */ @Service public class SensorAggregationService { public SensorStats computeStats(int[] readings) { // Tutto il calcolo avviene senza mai uscire dal dominio dei primitivi IntSummaryStatistics stats = IntStream.of(readings) .filter(v -> v >= 0 && v <= 10_000) // Filtro valori anomali .summaryStatistics(); return new SensorStats( stats.getMin(), stats.getMax(), stats.getAverage(), stats.getCount() ); } } /* Individuo i punti di autoboxing nascosto tramite JFR: in JDK Mission Control filtro gli eventi "Allocation in New TLAB" per tipo "java.lang.Integer" o "java.lang.Long". Se questi dominano l'allocation profiling, ho autoboxing da eliminare. */
```