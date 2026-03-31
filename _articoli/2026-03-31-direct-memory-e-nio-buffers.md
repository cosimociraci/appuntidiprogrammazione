---
layout: post
title: "Direct Memory e NIO Buffers"
date: 2026-03-31 19:21:16 
sintesi: "Molte librerie (Netty, gRPC) usano la Direct Memory (off-heap) per l'I/O veloce. Questa memoria non è gestita dal GC standard e non appare nel grafico dell'heap. Se non limitata con -XX:MaxDirectMemorySize, può crescere fino a rubare RAM al kernel. M"
tech: java
tags: [java, "jvm tuning & garbage collection"]
pdf_file: "direct-memory-e-nio-buffers.pdf"
---

## Esigenza Reale
Gestire le performance di un server socket ad alto throughput che usa buffer diretti per evitare la copia dei dati tra Java e OS.

## Analisi Tecnica
Problema: Memoria di sistema che sparisce nonostante l'heap Java risulti perfettamente stabile e sotto controllo. Perché: Imposto un limite alla memoria diretta. Ho scelto di allineare la Direct Memory alla dimensione dei buffer previsti, garantendo che lo storage off-heap non diventi una mina vagante per la stabilità del server.

## Esempio Implementativo

```java
/* Limito l'allocazione di buffer diretti NIO a 2GB, indipendentemente dalla
* dimensione dell'heap. Senza questo limite, la Direct Memory può crescere fino
* alla RAM disponibile del sistema, causando OOM Kill del kernel invisibile alla
* JVM. */ java -XX:MaxDirectMemorySize=2G \ -Xmx4G \
* -XX:+UnlockDiagnosticVMOptions \ -XX:NativeMemoryTracking=detail \ -jar netty-
* server.jar /* NativeMemoryTracking=detail permette di vedere la ripartizione
* completa della memoria nativa, inclusa la Direct Memory. */ /* Verifico la
* distribuzione della memoria nativa con jcmd: */ // jcmd <PID> VM.native_memory
* summary // Output atteso: // Total: reserved=8GB, committed=5GB // - Java
* Heap: reserved=4096MB, committed=4096MB // - Class: reserved=1GB,
* committed=62MB // - Thread: reserved=512MB, committed=512MB // - Internal:
* reserved=2GB, committed=1.8GB <-- qui c'è la Direct Memory /* Monitoro la
* Direct Memory in uso tramite JMX senza fermare l'applicazione: */
* @Scheduled(fixedDelay = 15_000) public void monitorDirectMemory() { try { //
* Accedo ai bean JMX interni per leggere l'utilizzo della Direct Memory Class<?>
* bitsClass = Class.forName("java.nio.Bits"); Field maxMemoryField =
* bitsClass.getDeclaredField("MAX_MEMORY"); maxMemoryField.setAccessible(true);
* Field reservedMemoryField = bitsClass.getDeclaredField("RESERVED_MEMORY");
* reservedMemoryField.setAccessible(true); long maxMemory = ((AtomicLong)
* maxMemoryField.get(null)).get(); long reservedMemory = ((AtomicLong)
* reservedMemoryField.get(null)).get(); double pct = 100.0 * reservedMemory /
* maxMemory; log.info("Direct Memory: {}MB / {}MB ({}%)", reservedMemory /
* 1_048_576, maxMemory / 1_048_576, String.format("%.1f", pct)); if (pct > 80) {
* alertService.sendWarning("Direct Memory all'80%: verificare leak di ByteBuffer
* diretti"); } } catch (Exception e) { log.warn("Impossibile leggere Direct
* Memory via reflection: {}", e.getMessage()); } } /* Alternativa moderna con
* Micrometer (Spring Boot Actuator espone già questa metrica): */ // GET
* /actuator/metrics/jvm.buffer.memory.used?tag=id:direct // GET
* /actuator/metrics/jvm.buffer.count?tag=id:direct /* Il leak più comune di
* Direct Memory avviene quando si allocano ByteBuffer.allocateDirect() senza
* rilasciarli esplicitamente. Il GC raccoglie l'oggetto Java wrapper ma non
* sempre libera immediatamente il buffer nativo sottostante. */ // SBAGLIATO:
* alloco un buffer diretto a ogni richiesta senza rilasciarlo public void
* processRequest(byte[] data) { ByteBuffer buffer =
* ByteBuffer.allocateDirect(data.length); // Leak potenziale buffer.put(data);
* sendToSocket(buffer); // Il buffer non viene mai liberato esplicitamente } //
* CORRETTO: riuso i buffer tramite pool (pattern usato da Netty internamente)
* @Component public class DirectBufferPool { private final Deque<ByteBuffer>
* pool = new ConcurrentLinkedDeque<>(); private static final int BUFFER_SIZE =
* 64 * 1024; // 64KB private static final int MAX_POOL_SIZE = 100; public
* ByteBuffer acquire() { ByteBuffer buf = pool.pollFirst(); if (buf == null) {
* buf = ByteBuffer.allocateDirect(BUFFER_SIZE); } buf.clear(); return buf; }
* public void release(ByteBuffer buf) { if (pool.size() < MAX_POOL_SIZE) {
* pool.offerFirst(buf); } else { // Supero il limite del pool: libero
* esplicitamente il buffer nativo ((sun.nio.ch.DirectBuffer)
* buf).cleaner().clean(); } } } /* Per liberare esplicitamente un ByteBuffer
* diretto quando necessario: */ public static void freeDirectBuffer(ByteBuffer
* buffer) { if (buffer.isDirect()) { ((sun.nio.ch.DirectBuffer)
* buffer).cleaner().clean(); } } /* In Spring Boot con Netty (es. WebFlux),
* configuro il pool di buffer Netty per limitare la Direct Memory: */ @Bean
* public NettyReactiveWebServerFactory nettyFactory() {
* NettyReactiveWebServerFactory factory = new NettyReactiveWebServerFactory();
* factory.addServerCustomizers(server -> server
* .option(ChannelOption.SO_BACKLOG, 1024) .childOption(ChannelOption.SO_RCVBUF,
* 32 * 1024) // 32KB recv buffer per connessione
* .childOption(ChannelOption.SO_SNDBUF, 32 * 1024) ); return factory; }
```
