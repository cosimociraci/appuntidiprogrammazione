---
layout: post
title: "Linker Options e Variadic Functions"
date: 2026-03-31 19:21:33 
sintesi: "Alcune funzioni C (come printf o ioctl) accettano un numero variabile di argomenti. Configurare i FunctionDescriptor variadici in Panama richiede di definire gli specializzatori per ogni combinazione di argomenti usata. Questo livello di dettaglio pe"
tech: java
tags: [java, "jni & project panama"]
pdf_file: "linker-options-e-variadic-functions.pdf"
---

## Esigenza Reale
Chiamare funzioni di sistema Unix/Linux complesse che richiedono flag e parametri dinamici.

## Analisi Tecnica
Problema: Difficoltà nel chiamare funzioni C flessibili che non hanno una firma fissa di parametri. Perché: Uso i descrittori variabili. Ho scelto di creare handle specifici per le diverse chiamate variadiche necessarie, garantendo che lo stack nativo venga preparato correttamente per ogni invocazione.

## Esempio Implementativo

```java
/* Le funzioni variadiche in C (quelle con ...) richiedono un FunctionDescriptor
* specializzato per ogni combinazione di argomenti che intendiamo usare. Non
* possiamo creare un handle "generico": ogni combinazione di tipi deve avere il
* suo handle dedicato. */ @Component public class SystemFunctionCaller { private
* final Linker linker = Linker.nativeLinker(); private final SymbolLookup stdlib
* = linker.defaultLookup(); // Handle per printf(const char* format, int value)
* private final MethodHandle printfInt; // Handle per printf(const char* format,
* double value) private final MethodHandle printfDouble; // Handle per
* printf(const char* format, const char* value) private final MethodHandle
* printfString; // Handle per ioctl(int fd, unsigned long request, struct*)
* private final MethodHandle ioctlStruct; @PostConstruct public void init()
* throws Exception { MemorySegment printfAddr =
* stdlib.find("printf").orElseThrow(); // Ogni variante variadica ha il suo
* FunctionDescriptor specifico printfInt = linker.downcallHandle( printfAddr,
* FunctionDescriptor.of(ValueLayout.JAVA_INT, ValueLayout.ADDRESS,
* ValueLayout.JAVA_INT), Linker.Option.firstVariadicArg(1) // Il primo argomento
* variadic è in posizione 1 ); printfDouble = linker.downcallHandle( printfAddr,
* FunctionDescriptor.of(ValueLayout.JAVA_INT, ValueLayout.ADDRESS,
* ValueLayout.JAVA_DOUBLE), Linker.Option.firstVariadicArg(1) ); printfString =
* linker.downcallHandle( printfAddr, FunctionDescriptor.of(ValueLayout.JAVA_INT,
* ValueLayout.ADDRESS, ValueLayout.ADDRESS), Linker.Option.firstVariadicArg(1)
* ); // ioctl con struct: usato per configurare device driver Linux
* MemorySegment ioctlAddr = stdlib.find("ioctl").orElseThrow(); ioctlStruct =
* linker.downcallHandle( ioctlAddr, FunctionDescriptor.of(ValueLayout.JAVA_INT,
* ValueLayout.JAVA_INT, ValueLayout.JAVA_LONG, ValueLayout.ADDRESS) ); } /* Uso
* gli handle per chiamare le funzioni variadiche: */ public void
* demonstratePrintf() throws Throwable { try (Arena arena = Arena.ofConfined())
* { MemorySegment intFormat = arena.allocateFrom("Valore intero: %d
"); MemorySegment dblFormat = arena.allocateFrom("Valore double: %.2f
"); MemorySegment strFormat = arena.allocateFrom("Stringa: %s
"); MemorySegment strValue = arena.allocateFrom("Hello Panama!");
printfInt.invokeExact(intFormat, 42); printfDouble.invokeExact(dblFormat,
3.14159); printfString.invokeExact(strFormat, strValue); } } /* Uso ioctl per
configurare un'interfaccia di rete tramite il kernel Linux: */ public void
configureNetworkInterface(int socketFd, NetworkConfig config) throws Throwable {
try (Arena arena = Arena.ofConfined()) { // Alloco la struct ifreq per passare i
parametri al kernel MemorySegment ifreq = arena.allocate(IFREQ_LAYOUT); //
Scrivo il nome dell'interfaccia nel campo ifr_name MemorySegment ifName =
arena.allocateFrom(config.getInterfaceName()); ifreq.asSlice(0,
16).copyFrom(ifName.asSlice(0, Math.min(15, ifName.byteSize()))); // Chiamo
ioctl con SIOCSIFMTU per impostare il MTU IFREQ_MTU_VH.set(ifreq, 0L,
config.getMtu()); int result = (int) ioctlStruct.invokeExact(socketFd,
SIOCSIFMTU, ifreq); if (result < 0) throw new IOException("ioctl SIOCSIFMTU
fallita per " + config.getInterfaceName()); log.info("MTU impostato a {} su {}",
config.getMtu(), config.getInterfaceName()); } } } /* In Spring Boot, registro i
SystemFunctionCaller come Bean e lo uso nei service che devono interagire con il
sistema operativo: */ @Service public class NetworkManagementService {
@Autowired private SystemFunctionCaller systemCaller; public void
tuneNetworkInterfaces(List<NetworkConfig> configs) { try (var scope = new
StructuredTaskScope.ShutdownOnFailure()) { for (NetworkConfig config : configs)
{ scope.fork(() -> { int fd = openSocket(); try {
systemCaller.configureNetworkInterface(fd, config); } finally { closeSocket(fd);
} return null; }); } scope.join().throwIfFailed(); } catch (Exception e) { throw
new NetworkConfigurationException("Errore configurazione interfacce", e); } } }
```
