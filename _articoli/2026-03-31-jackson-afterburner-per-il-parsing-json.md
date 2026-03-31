---
layout: post
title: "Jackson Afterburner per il Parsing JSON"
date: 2026-03-31 17:02:46 
sintesi: "La reflection standard usata dai parser JSON è lenta. I moduli jackson-module-afterburner (Java 8) e jackson-module-blackbird (Java 11+) usano la generazione di bytecode a runtime per creare "accessori" diretti ai campi della classe, eliminando l'ove"
tech: java
tags: ['java', 'memory & performance']
pdf_file: "jackson-afterburner-per-il-parsing-json.pdf"
---

## Esigenza Reale
Accelerare i tempi di risposta di un'API REST che restituisce grandi liste di oggetti complessi.

## Analisi Tecnica
Problema: Il tempo speso nella serializzazione JSON domina il tempo totale della richiesta a causa della lentezza della reflection. Perché: Abilito la generazione di bytecode dinamico. Ho scelto di ottimizzare il layer di trasporto delegando a Jackson la creazione di invocatori ottimizzati per i miei DTO specifici.

## Esempio Implementativo

```java
/* Configuro l'ObjectMapper con Blackbird (il successore moderno di Afterburner per Java 11+). Blackbird genera bytecode a runtime che accede direttamente ai campi senza passare per la reflection. */ @Configuration public class JacksonConfig { @Bean @Primary public ObjectMapper objectMapper() { return new ObjectMapper() .registerModule(new BlackbirdModule()) // Java 11+: usa invoke dynamic invece di bytecode ASM .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false) .configure(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false) .registerModule(new JavaTimeModule()); } } /* Verifico il guadagno con JMH confrontando la serializzazione con e senza Blackbird: */ @State(Scope.Benchmark) public class JacksonBenchmark { private ObjectMapper standardMapper = new ObjectMapper(); private ObjectMapper blackbirdMapper = new ObjectMapper().registerModule(new BlackbirdModule()); private OrderResponse largePayload = generateLargePayload(100); // 100 ordini @Benchmark @BenchmarkMode(Mode.Throughput) public byte[] withStandardReflection() throws Exception { return standardMapper.writeValueAsBytes(largePayload); } @Benchmark @BenchmarkMode(Mode.Throughput) public byte[] withBlackbird() throws Exception { return blackbirdMapper.writeValueAsBytes(largePayload); } // Risultato tipico: withBlackbird ha 30-40% di throughput in più su payload grandi } /* Per massimizzare ulteriormente le performance, combino Blackbird con @JsonView per serializzare solo i campi necessari per ogni endpoint, riducendo la dimensione del payload: */ public class Views { public interface Summary {} public interface Detail extends Summary {} } @JsonView(Views.Summary.class) public class OrderDto { private Long id; private String status; private BigDecimal total; @JsonView(Views.Detail.class) // Serializzato solo nella vista Detail private List<OrderItemDto> items; @JsonView(Views.Detail.class) private String shippingAddress; } /* Nel controller uso @JsonView per selezionare la vista: */ @RestController public class OrderController { @GetMapping("/orders") @JsonView(Views.Summary.class) // Serializza solo id, status, total: payload 80% più piccolo public List<OrderDto> listOrders() { return orderService.findAll(); } @GetMapping("/orders/{id}") @JsonView(Views.Detail.class) // Serializza tutto public OrderDto getOrder(@PathVariable Long id) { return orderService.findById(id); } } /* Per payload JSON ricevuti in ingresso, configuro anche il buffer di parsing per evitare riallocazioni: */ @Bean public Jackson2ObjectMapperBuilderCustomizer jacksonCustomizer() { return builder -> builder .featuresToEnable(JsonParser.Feature.ALLOW_MISSING_VALUES) .postConfigurer(mapper -> { mapper.getFactory().setStreamReadConstraints( StreamReadConstraints.builder() .maxStringLength(10_000_000) // 10MB max per singola stringa JSON .build()); }); }
```
