---
layout: post
title: "Annotation Processing (JSR 269)"
date: 2026-04-03 14:39:40
sintesi: "Leggere le annotazioni tramite Reflection a runtime rallenta lo startup dell'applicazione. Gli Annotation Processors spostano la logica a Compile Time- framework come MapStruct o Lombok generano codice Java reale durante la compilazione. Questo elimi"
tech: "java"
tags: ["java", "advanced reflection & metaprogr"]
pdf_file: "annotation-processing-jsr-269.pdf"
---

## Esigenza Reale
Generare automaticamente il codice di mapping tra DTO e Entity senza usare librerie basate su reflection a runtime.

## Analisi Tecnica
Problema: Latenza di avvio elevata (startup time) dovuta allo scanning intensivo delle annotazioni su migliaia di classi. Perché: Implemento un Annotation Processor. Ho scelto di generare il codice sorgente durante la build così che a runtime l'applicazione esegua solo codice Java "plain", senza introspezione.

## Esempio Implementativo

```java
/* Definisco l'annotazione che triggera la generazione del codice di mapping. */
 @Retention(RetentionPolicy.SOURCE) 
// Disponibile solo a compile time: zero overhead a runtime
// @Target(ElementType.TYPE) public @interface GenerateMapper
{ Class<?> target(); 
// La classe di destinazione del mapping }
 
/* Implemento il processor che genera il mapper durante la compilazione: */
 @SupportedAnnotationTypes("com.myapp.GenerateMapper")
@SupportedSourceVersion(SourceVersion.RELEASE_17) public class MapperProcessor
extends AbstractProcessor
{ @Override public boolean process(Set<? extends TypeElement> annotations,
RoundEnvironment roundEnv)
{ for (Element element :
roundEnv.getElementsAnnotatedWith(GenerateMapper.class))
{ TypeElement sourceClass = (TypeElement) element; GenerateMapper annotation =
sourceClass.getAnnotation(GenerateMapper.class);
// Genero il file sorgente del mapper try 
{ generateMapperClass(sourceClass, annotation); }
 catch (IOException e) 
{ processingEnv.getMessager().printMessage( Diagnostic.Kind.ERROR, "Errore
generazione mapper: " + e.getMessage(), element); }
 }
 return true; }
 private void generateMapperClass(TypeElement sourceClass, GenerateMapper
annotation) throws IOException
{ String mapperName = sourceClass.getSimpleName() + "Mapper"; JavaFileObject
file = processingEnv.getFiler().createSourceFile(
processingEnv.getElementUtils().getPackageOf(sourceClass) + "." + mapperName);
try (PrintWriter writer = new PrintWriter(file.openWriter()))
{ writer.println("package " +
processingEnv.getElementUtils().getPackageOf(sourceClass) + ";");
writer.println("
// GENERATED CODE - DO NOT EDIT"); writer.println("public class " + mapperName +
// "
{"); 
// Genero i metodi di mapping per ogni campo della classe sorgente for (Element
// field : sourceClass.getEnclosedElements())
{ if (field.getKind() == ElementKind.FIELD) 
{ String fieldName = field.getSimpleName().toString(); String capitalizedField =
Character.toUpperCase(fieldName.charAt(0)) + fieldName.substring(1);
writer.println(" public void map" + capitalizedField + "(Object source, Object
target)
{"); writer.println(" 
// Mapping generato a compile time: zero reflection"); writer.println(" }
"); }
 }
 writer.println("}
"); }
 }
 }
 
* Registro il processor nel file META-
* INF/services/javax.annotation.processing.Processor: */
 
// com.myapp.MapperProcessor 
/* Uso l'annotation nel codice sorgente: */
 @GenerateMapper(target = OrderDto.class) public class Order 
{ private Long id; private String status; private BigDecimal total; }
 
* A compile time viene generato OrderMapper.java con metodi di mapping diretti.
* A runtime, lo uso senza reflection: */
 @Service public class OrderService 
{ 
// Inietto il mapper generato: è codice Java puro, zero reflection private final
// OrderMapper mapper = new OrderMapper(); public OrderDto toDto(Order order)
{ OrderDto dto = new OrderDto(); mapper.mapId(order, dto);
mapper.mapStatus(order, dto); mapper.mapTotal(order, dto); return dto;
// Tutto il mapping è codice generato: il JIT lo ottimizza perfettamente }
 }
 
* In Spring Boot, combino l'Annotation Processor con GraalVM Native Image: il
* codice generato a compile time è nativo-friendly, mentre il codice basato su
* reflection richiede configurazioni aggiuntive per la compilazione nativa. */
```
