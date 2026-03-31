---
layout: post
title: TLAB (Thread-Local Allocation Buffers)
date: '2026-03-31 16:25:00 '
sintesi: 'L''Eden space è una risorsa condivisa: se ogni thread dovesse bloccare l''intero
  spazio per ogni new, il multithreading sarebbe lentissimo. I TLAB assegnano a ogni
  thread una piccola porzione privata dell''Eden dove allocare oggetti senza lock.
  Se i TLA'
esigenza: Ridurre i colli di bottiglia durante i picchi di traffico in un'applicazione
  che crea milioni di oggetti DTO temporanei per ogni richiesta.
tech: java
tags:
- java
- jvm tuning & garbage collection
codice: '/* Abilito il logging dettagliato dei TLAB per capire se la dimensione di
  default è sufficiente per il mio carico. */ java -XX:+UnlockDiagnosticVMOptions
  \ -XX:+PrintTLAB \ -XX:+UseTLAB \ -Xlog:tlab*=debug:file=tlab.log:time \ -jar my-app.jar
  /* Nel log cerco i seguenti indicatori di problema: */ // [tlab] TLAB: gc thread:
  0x... [id: 23] desired_size: 512KB slow allocs: 142 // Se ''slow allocs'' è alto,
  il thread sta chiedendo nuovo TLAB troppo spesso /* Aumento la dimensione minima
  del TLAB per ridurre la frequenza di riallocazione: */ java -XX:+UseTLAB \ -XX:TLABSize=512k
  \ // Dimensione iniziale suggerita -XX:MinTLABSize=64k \ // Dimensione minima garantita
  -XX:TLABWasteTargetPercent=5 \ // Accetto fino al 5% di spreco per evitare slow
  allocs -jar my-app.jar /* Identifico i metodi che allocano più oggetti tramite JFR
  per ridurre la pressione sui TLAB alla radice: */ // jcmd <PID> JFR.start name=alloc
  settings=profile // Aspetto 60 secondi di traffico reale // jcmd <PID> JFR.dump
  filename=alloc.jfr // In JDK Mission Control apro l''evento "Allocation in New TLAB"
  ordinato per dimensione /* La strategia più efficace è ridurre le allocazioni stesse.
  In Spring Boot, uso object pooling per i DTO che vengono creati e distrutti milioni
  di volte: */ @Component public class OrderDtoPool { private final ObjectPool<OrderDto>
  pool = new GenericObjectPool<>(new BasePooledObjectFactory<>() { @Override public
  OrderDto create() { return new OrderDto(); } @Override public PooledObject<OrderDto>
  wrap(OrderDto dto) { return new DefaultPooledObject<>(dto); } }); public OrderDto
  borrow() throws Exception { return pool.borrowObject(); } public void returnToPool(OrderDto
  dto) { dto.reset(); // Pulisco lo stato prima di restituire pool.returnObject(dto);
  } } /* Oppure uso record Java per DTO immutabili: la JVM può ottimizzare meglio
  la loro allocazione grazie all''analisi di escape: */ public record OrderSummaryDto(long
  id, String status, BigDecimal total) {} // La JVM può allocare questo record sullo
  stack invece che sull''heap se non "sfugge" al metodo /* Monitoro la pressione di
  allocazione con Micrometer: */ Gauge.builder("jvm.tlab.slow_allocs", () -> getTlabSlowAllocCount())
  .description("Numero di allocazioni lente fuori TLAB") .register(meterRegistry);'
---

Problema: Rallentamento delle allocazioni di memoria dovuto alla sincronizzazione tra i thread nel Memory Manager della JVM. Perché: Verifico e ottimizzo i TLAB. Ho scelto di assicurarmi che l'allocazione sia "lock-free" per la stragrande maggioranza degli oggetti, riducendo drasticamente il tempo speso nei safepoint.