---
layout: post
title: "Java Flight Recorder (JFR) in Prod"
date: 2026-04-03 14:39:38
sintesi: "Diagnosticare problemi di performance dopo che sono avvenuti  quasi impossibile senza dati storici. JFR  uno strumento a basso overhead (<1%) da tenere sempre attivo in produzione. JFR registra eventi interni della JVM (allocazioni, lock, pause GC,"
tech: "java"
tags: ["java", "jvm tuning & garbage collection"]
pdf_file: "java-flight-recorder-jfr-in-prod.pdf"
---

## Esigenza Reale
Risolvere bug intermittenti o rallentamenti che si verificano solo sotto carichi di produzione particolari e non sono riproducibili localmente.

## Analisi Tecnica
Problema: Mancanza di visibilità granulare sui micro-eventi interni della JVM durante i picchi di traffico reale. Perché: Attivo JFR in modalità continua. Ho scelto questa tecnologia perché l'impatto sulle prestazioni è trascurabile, ma il valore dei dati raccolti per il debugging post-mortem è inestimabile.

## Esempio Implementativo

```java
* Avvio la registrazione continua degli eventi JVM. maxsize=1g mantiene solo
* l'ultimo 1GB di eventi, sovrascrivendo i dati più vecchi in modalità
* circolare: la "scatola nera" è sempre piena degli ultimi N minuti di attività.
* */
 java -XX:StartFlightRecording=disk=true,\ dumponexit=true,\ maxsize=1g,\
maxage=1h,\ filename=/var/log/jfr/recording.jfr,\ settings=profile \ -jar
mission-critical-app.jar
* Per scaricare il recording senza fermare l'applicazione, identifico il PID e
* uso jcmd: */
 
// jcmd <PID> JFR.dump filename=/tmp/incident-$(date +%Y%m%d_%H%M%S).jfr 
// Il file .jfr viene creato istantaneamente: contiene gli ultimi 60 minuti di
// eventi JVM
* Avvio una registrazione mirata di 60 secondi in risposta a un alert di
* produzione: */
 
// jcmd <PID> JFR.start name=incident duration=60s filename=/tmp/incident.jfr
// settings=profile
* Creo un profilo JFR custom per catturare eventi specifici alla mia
* applicazione, con overhead minimo: */
 @Component public class CustomJfrEvents 
{ 
* Definisco un evento JFR custom per tracciare le operazioni lente del mio
* dominio. */
 static class SlowOrderEvent extends jdk.jfr.Event 
{ @jdk.jfr.Label("Order ID") long orderId; @jdk.jfr.Label("Duration ms") long
durationMs; @jdk.jfr.Label("Operation") String operation; }
 public void processOrder(long orderId) 
{ SlowOrderEvent event = new SlowOrderEvent(); event.begin(); 
// Avvio la registrazione temporale try 
{ doProcessOrder(orderId); }
 finally 
{ event.orderId = orderId; event.durationMs = event.getDuration().toMillis();
event.operation = "processOrder"; event.commit();
// Scrivo l'evento nel JFR buffer solo se l'evento è abilitato }
 }
 }
 
* Aggiungo il file di configurazione JFR custom (custom-profile.jfc) per ridurre
* l'overhead al minimo: */
 
// <configuration version="2.0"> 
// <event name="com.myapp.SlowOrderEvent"> 
// <setting name="enabled">true</setting> 
// <setting name="threshold">100 ms</setting> <!-- Registro solo gli eventi >
// 100ms -->
// </event> 
// <event name="jdk.ThreadSleep"> 
// <setting name="enabled">true</setting> 
// <setting name="threshold">10 ms</setting> 
// </event> 
// </configuration> 
* In Spring Boot, automatizzo il dump JFR quando viene rilevato un alert critico
* (es. latenza p99 > soglia): */
 @Component public class JfrDumpOnAlert 
{ @EventListener public void onLatencyAlert(HighLatencyAlertEvent alert) 
{ try 
{ String filename = "/var/log/jfr/alert-" + System.currentTimeMillis() + ".jfr";
// Eseguo il dump tramite l'API JFR programmatica (Java 9+) for (Recording
// recording : FlightRecorder.getFlightRecorder().getRecordings())
{ if (recording.getState() == RecordingState.RUNNING) 
{ recording.dump(Path.of(filename)); log.info("JFR dump salvato automaticamente
in
{}
 per alert: 
{}
", filename, alert.getReason()); break; }
 }
 }
 catch (IOException e) 
{ log.error("Impossibile salvare il JFR dump", e); }
 }
 }
 
* Carico il .jfr in JDK Mission Control per l'analisi: le view più utili sono: -
* Method Profiling: quale metodo consuma più CPU (campionamento a 10ms) - Lock
* Instances: quali lock sono contesi e per quanto tempo - Allocation in New
* TLAB: quali classi allocano più memoria - Socket Read/Write: quali host
* causano latenza I/O - GC Configuration e GC Pauses: configurazione e pause
* effettive del GC */
```
