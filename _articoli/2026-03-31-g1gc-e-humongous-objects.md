---
layout: post
title: "G1GC e Humongous Objects"
date: 2026-03-31 17:02:46 
sintesi: "G1 divide l'heap in regioni. Se un oggetto occupa più del 50% di una regione, viene considerato "Humongous" e allocato direttamente nella Old Generation, saltando l'Eden. Troppi Humongous objects causano frammentazione e pause pesanti. Aumentare G1He"
tech: java
tags: ['java', 'jvm tuning & garbage collection']
pdf_file: "g1gc-e-humongous-objects.pdf"
---

## Esigenza Reale
Ottimizzare la gestione di grandi buffer di byte usati per processare immagini o file PDF caricati in memoria.

## Analisi Tecnica
Problema: Frammentazione prematura dell'heap e cicli di GC frequenti dovuti a allocazioni di oggetti troppo grandi per le regioni standard. Perché: Aumento la dimensione della regione G1. Ho scelto questa configurazione per permettere al GC di trattare i buffer come oggetti a vita breve, pulendoli durante le "Young GC" senza sporcare la Old Gen.

## Esempio Implementativo

```java
/* Imposto la dimensione della regione a 32MB (il massimo consentito) per evitare la classificazione humongous di buffer fino a 16MB. Con regioni da 8MB (default con heap da 8GB), un buffer da 5MB è già Humongous. */ java -XX:+UseG1GC \ -XX:G1HeapRegionSize=32M \ -Xms16G -Xmx16G \ -XX:G1HeapWastePercent=5 \ -Xlog:gc*,gc+humongous=debug:file=gc.log:time \ -jar image-service.jar /* Verifico nel log quanti oggetti Humongous vengono allocati prima della modifica: */ // [gc+humongous] Allocating humongous object of size 5242880 // Se questo appare migliaia di volte, la configurazione regione è sbagliata /* Dopo aver aumentato G1HeapRegionSize=32M, un buffer da 5MB non supera più il 50% della regione: viene allocato nell'Eden e pulito dalla Young GC in pochi millisecondi. */ /* Identifico i punti del codice che allocano oggetti Humongous tramite JFR: */ // jcmd <PID> JFR.start name=humongous settings=default // jcmd <PID> JFR.dump filename=humongous.jfr // Apro il .jfr con JDK Mission Control e filtro per eventi "Object Allocation in New TLAB" > 4MB /* In Spring Boot, il servizio che processa le immagini deve rilasciare i buffer immediatamente dopo l'uso per permettere alla Young GC di raccoglierli: */ @Service public class ImageProcessingService { public byte[] processImage(MultipartFile file) throws IOException { byte[] imageBytes = file.getBytes(); // Alloco il buffer try { BufferedImage img = ImageIO.read(new ByteArrayInputStream(imageBytes)); BufferedImage processed = applyFilters(img); ByteArrayOutputStream out = new ByteArrayOutputStream(); ImageIO.write(processed, "jpeg", out); return out.toByteArray(); } finally { imageBytes = null; // Aiuto il GC a raccogliere il buffer di input // Il buffer uscirà dallo scope e sarà eleggibile per la prossima Young GC } } } /* Monitoro il tasso di allocazioni Humongous tramite JMX per verificare l'efficacia della modifica: */ @Scheduled(fixedDelay = 30_000) public void monitorHumongousAllocations() { for (GarbageCollectorMXBean gc : ManagementFactory.getGarbageCollectorMXBeans()) { GarbageCollectorMXBean g1 = ManagementFactory.getGarbageCollectorMXBeans() .stream().filter(b -> b.getName().contains("G1")).findFirst().orElse(null); if (g1 != null) { log.info("G1 GC count: {}, time: {}ms", g1.getCollectionCount(), g1.getCollectionTime()); } } }
```
