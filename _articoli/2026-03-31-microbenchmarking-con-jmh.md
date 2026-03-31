---
layout: post
title: Microbenchmarking con JMH
date: '2026-03-31 16:25:01 '
sintesi: Misurare le performance con System.currentTimeMillis() è sbagliato a causa
  del JIT warmup e delle ottimizzazioni JVM. JMH (Java Microbenchmark Harness) è lo
  standard industriale per misurare nanosecondi reali, gestendo le fasi di riscaldamento
  e evit
esigenza: Decidere oggettivamente quale tra due implementazioni di un algoritmo è
  la più efficiente per il sistema.
tech: java
tags:
- java
- memory & performance
codice: '/* Configurazione Maven per JMH: aggiungo le dipendenze e il plugin per generare
  il JAR eseguibile. */ // <dependency> // <groupId>org.openjdk.jmh</groupId> // <artifactId>jmh-core</artifactId>
  // <version>1.37</version> // </dependency> // <dependency> // <groupId>org.openjdk.jmh</groupId>
  // <artifactId>jmh-generator-annprocess</artifactId> // <version>1.37</version>
  // <scope>provided</scope> // </dependency> /* Implemento un benchmark completo
  che confronta due strategie di concatenazione stringhe: */ @BenchmarkMode({Mode.Throughput,
  Mode.AverageTime}) @OutputTimeUnit(TimeUnit.MICROSECONDS) @State(Scope.Thread) //
  Ogni thread ha la sua istanza dello State @Warmup(iterations = 5, time = 1, timeUnit
  = TimeUnit.SECONDS) // 5s di warmup JIT @Measurement(iterations = 10, time = 2,
  timeUnit = TimeUnit.SECONDS) @Fork(2) // Eseguo in 2 JVM separate per eliminare
  il rumore public class StringConcatBenchmark { @Param({"10", "100", "1000"}) //
  JMH esegue il benchmark per ogni valore del param private int iterations; @Benchmark
  public String withStringConcat() { String result = ""; for (int i = 0; i < iterations;
  i++) { result += "item" + i; // Alloca una nuova String ad ogni iterazione } return
  result; // Ritorno il risultato: JMH lo usa per evitare la Dead Code Elimination
  } @Benchmark public String withStringBuilder() { StringBuilder sb = new StringBuilder(iterations
  * 8); for (int i = 0; i < iterations; i++) { sb.append("item").append(i); } return
  sb.toString(); // Ritorno il risultato: essenziale per evitare che JIT elimini il
  codice } /* @Benchmark public String withStringJoin() { // JMH gestisce automaticamente
  il warmup del JIT per questo metodo return String.join("", IntStream.range(0, iterations)
  .mapToObj(i -> "item" + i) .toArray(String[]::new)); } */ } /* Eseguo il benchmark
  e leggo i risultati: */ // java -jar target/benchmarks.jar StringConcatBenchmark
  -rf json -rff results.json // Output: // Benchmark Mode Cnt Score Error Units //
  withStringConcat thrpt 20 12.345 ± 0.123 ops/us // withStringBuilder thrpt 20 987.654
  ± 9.876 ops/us /* Errori comuni che JMH evita automaticamente: */ // 1. Dead Code
  Elimination: JIT elimina codice il cui risultato non è usato // --> JMH usa Blackhole
  per "consumare" i risultati senza influire sul timing @Benchmark public void withBlackhole(Blackhole
  bh) { String result = expensiveOperation(); bh.consume(result); // Segnala alla
  JVM che il risultato è usato } // 2. Constant Folding: JIT pre-calcola espressioni
  costanti // --> @State garantisce che i valori siano letti a runtime, non pre-calcolati
  @State(Scope.Benchmark) public static class BenchmarkState { public int value =
  Integer.parseInt("42"); // Impedisce il constant folding } /* In Spring Boot, integro
  JMH come test separato nella CI per regressionare le performance: */ @Test public
  void runJmhBenchmarks() throws Exception { Options opt = new OptionsBuilder() .include(StringConcatBenchmark.class.getSimpleName())
  .warmupIterations(3) .measurementIterations(5) .forks(1) .resultFormat(ResultFormatType.JSON)
  .result("target/jmh-results.json") .build(); Collection<RunResult> results = new
  Runner(opt).run(); for (RunResult result : results) { double score = result.getPrimaryResult().getScore();
  String name = result.getParams().getBenchmark(); // Fallisco il test se le performance
  regrediscono oltre il 10% rispetto alla baseline assertTrue(score > getBaseline(name)
  * 0.9, "Regressione di performance su: " + name); } }'
---

Problema: Ottimizzazioni basate su misurazioni empiriche errate che non tengono conto del comportamento del compilatore JIT. Perché: Uso lo standard industriale JMH. Ho scelto questo strumento per isolare il codice sotto test e ottenere metriche statisticamente significative, eliminando il rumore della JVM.