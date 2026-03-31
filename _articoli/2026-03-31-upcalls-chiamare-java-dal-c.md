---
layout: post
title: 'Upcalls: Chiamare Java dal C'
date: '2026-03-31 16:25:01 '
sintesi: A volte è il codice C che deve inviare una notifica a Java (callback). Panama
  permette di creare "stub" per le upcall tramite linker.upcallStub(). Le upcall sono
  più lente delle downcall (Java -> C) perché devono ricreare il contesto Java. Vanno
  prog
esigenza: Implementare un sistema di monitoraggio dove una libreria C notifica a Java
  il superamento di una soglia di temperatura.
tech: java
tags:
- java
- jni & project panama
codice: '/* Definisco il metodo Java che verrà chiamato dalla libreria C come callback.
  Il metodo deve essere static per poter essere convertito in un MethodHandle senza
  binding all''istanza. */ public class TemperatureMonitor { // Questo metodo viene
  chiamato dalla libreria C quando la temperatura supera la soglia public static void
  onTemperatureAlert(float temperature, int sensorId) { log.warn("ALERT: sensore {}
  ha raggiunto {}°C", sensorId, temperature); meterRegistry.counter("temperature.alert",
  "sensor", String.valueOf(sensorId)).increment(); alertService.sendCritical("Temperatura
  critica: " + temperature + "°C su sensore " + sensorId); } } /* Registro il callback
  con la libreria C di monitoraggio hardware: */ @Service public class HardwareMonitoringService
  { private final Arena callbackArena = Arena.ofShared(); // Shared: il C può chiamarlo
  da qualsiasi thread private MemorySegment callbackPtr; @PostConstruct public void
  init() throws Throwable { Linker linker = Linker.nativeLinker(); SymbolLookup monitorLib
  = SymbolLookup.libraryLookup("libhw_monitor.so", Arena.global()); // Creo il MethodHandle
  per il metodo Java di callback MethodHandle onAlertHandle = MethodHandles.lookup().findStatic(
  TemperatureMonitor.class, "onTemperatureAlert", MethodType.methodType(void.class,
  float.class, int.class) ); // Descrivo la firma della funzione C del callback: void
  (*callback)(float temp, int sensor_id) FunctionDescriptor callbackDescriptor = FunctionDescriptor.ofVoid(
  ValueLayout.JAVA_FLOAT, ValueLayout.JAVA_INT ); // Trasformo il MethodHandle in
  un puntatore a funzione che il C può chiamare callbackPtr = linker.upcallStub(onAlertHandle,
  callbackDescriptor, callbackArena); // Registro il callback con la libreria nativa
  MethodHandle registerCallback = linker.downcallHandle( monitorLib.find("register_temperature_callback").orElseThrow(),
  FunctionDescriptor.ofVoid(ValueLayout.ADDRESS, ValueLayout.JAVA_FLOAT) ); registerCallback.invokeExact(callbackPtr,
  85.0f); // Soglia: 85°C log.info("Callback temperatura registrato: soglia 85°C");
  } @PreDestroy public void cleanup() { // Deregistro il callback prima di chiudere
  l''Arena per evitare che il C chiami un puntatore pendente deregisterCallbackFromLibrary();
  callbackArena.close(); // Ora il puntatore è invalido: nessun dangling pointer }
  } /* Per callback ad alta frequenza dove la latenza conta, uso un buffer ad anello
  invece di upcall dirette. Il C scrive gli eventi nel buffer, Java lo legge periodicamente
  senza upcall: */ @Service public class HighFrequencyEventService { private final
  MemorySegment ringBuffer; private final MemorySegment writeIndex; private final
  MemorySegment readIndex; public HighFrequencyEventService() { Arena arena = Arena.ofShared();
  // Buffer ad anello da 1MB per 65536 eventi da 16 byte ciascuno ringBuffer = arena.allocate(65536
  * 16); writeIndex = arena.allocate(ValueLayout.JAVA_INT); readIndex = arena.allocate(ValueLayout.JAVA_INT);
  // Il C riceve il puntatore al buffer e scrive direttamente senza upcall initNativeRingBuffer(ringBuffer,
  writeIndex, 65536); } @Scheduled(fixedDelay = 1) // Poll ogni millisecondo public
  void pollEvents() { int wIdx = (int) ValueLayout.JAVA_INT.varHandle().get(writeIndex,
  0L); int rIdx = (int) ValueLayout.JAVA_INT.varHandle().get(readIndex, 0L); while
  (rIdx != wIdx) { long offset = (long)(rIdx % 65536) * 16; processEvent(ringBuffer.asSlice(offset,
  16)); rIdx = (rIdx + 1) & 0xFFFF; } ValueLayout.JAVA_INT.varHandle().set(readIndex,
  0L, rIdx); } }'
---

Problema: Necessità di gestire eventi asincroni generati dal mondo nativo senza bloccare l'esecuzione. Perché: Creo un upcallStub. Ho scelto di mappare un metodo Java come puntatore a funzione C, permettendo alla libreria esterna di "chiamare casa" in modo sicuro e controllato.