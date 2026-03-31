---
layout: post
title: "SpEL Compilation Mode"
date: 2026-03-31 18:54:47 
sintesi: "Di default, Spring interpreta le espressioni SpEL ogni volta, il che è lento. La modalità spring.expression.compiler.mode=IMMEDIATE forza il compilatore a generare bytecode Java reale per le espressioni più frequenti. Questo riduce drasticamente i ci"
tech: thymeleaf
tags: [thymeleaf, "performance tuning & caching"]
pdf_file: "spel-compilation-mode.pdf"
---

## Esigenza Reale
Accelerare il rendering di dashboard complesse con centinaia di punti dati e accessi a proprietà annidate.

## Analisi Tecnica
Problema: Overhead eccessivo di CPU dovuto all'interpretazione continua di espressioni dinamiche durante il rendering. Perché: Uso la compilazione JIT di SpEL. Ho scelto la modalità IMMEDIATE per trasformare le lookup di proprietà in chiamate a metodi dirette nel bytecode, eliminando la riflessione runtime.

## Esempio Implementativo

```thymeleaf
# application.properties: abilito la compilazione SpEL in modalità IMMEDIATE. # Con OFF (default):
ogni espressione viene interpretata tramite un AST a ogni rendering. # Con IMMEDIATE: la prima
esecuzione compila l'espressione in bytecode; le successive la eseguono nativamente. # Con MIXED:
SpEL compila automaticamente le espressioni che falliscono silenziosamente invece di lanciare
eccezioni. spring.expression.compiler.mode=IMMEDIATE /* Verifico l'impatto con un benchmark JMH su
una dashboard con 500 righe e accessi a proprietà annidate. */ @BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS) public class SpelBenchmark { private SpelExpressionParser
parser; private StandardEvaluationContext context; @Setup public void setup() { // Configurazione
SENZA compilazione SpelParserConfiguration config = new SpelParserConfiguration(
SpelCompilerMode.OFF, getClass().getClassLoader()); parser = new SpelExpressionParser(config); //
Per il benchmark CON compilazione: // config = new
SpelParserConfiguration(SpelCompilerMode.IMMEDIATE, ...) context = new StandardEvaluationContext(new
DashboardData(generateRows(500))); } @Benchmark public Object withoutCompilation() { // Ogni
chiamata interpreta l'AST: reflection ad ogni accesso return
parser.parseExpression("rows[0].metrics.revenue.formatted").getValue(context); } } /* Configuro la
compilazione SpEL programmaticamente per avere controllo granulare: */ @Configuration public class
SpelConfig { @Bean public SpelExpressionParser spelParser() { SpelParserConfiguration config = new
SpelParserConfiguration( SpelCompilerMode.IMMEDIATE, Thread.currentThread().getContextClassLoader()
); return new SpelExpressionParser(config); } } /* ATTENZIONE: la modalità IMMEDIATE ha limitazioni.
Evito di usarla per: 1. Espressioni che accedono a tipi null (causa NullPointerException nel
bytecode compilato) 2. Espressioni con tipi che cambiano a runtime (il bytecode generato è
specializzato per il tipo visto la prima volta) 3. Espressioni che usano operatori di Elvis (?:) su
oggetti che cambiano tipo */ // Espressione sicura per la compilazione (tipo stabile, mai null): //
${product.price.doubleValue()} // Espressione NON adatta alla compilazione (tipo variabile o
nullable): // ${product.discount?.percentage} <- l'operatore safe-navigation causa problemi con
IMMEDIATE /* Per ambienti ad alto traffico, configuro anche il caching del template resolver: */
@Bean public SpringResourceTemplateResolver templateResolver() { SpringResourceTemplateResolver
resolver = new SpringResourceTemplateResolver(); resolver.setCacheable(true); // FONDAMENTALE in
produzione resolver.setCacheTTLMs(null); // null = cache infinita (invalidata solo al restart)
resolver.setCharacterEncoding("UTF-8"); return resolver; } /* Misuro il guadagno in produzione
tramite Micrometer: */ @Bean public TimedAspect timedAspect(MeterRegistry registry) { return new
TimedAspect(registry); } @Timed(value = "thymeleaf.rendering", histogram = true) public String
renderDashboard(Model model) { // Il tempo di rendering è ora visibile su
/actuator/metrics/thymeleaf.rendering return "dashboard"; }

```
