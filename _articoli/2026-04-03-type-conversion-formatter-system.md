---
layout: post
title: "Type Conversion & Formatter System"
date: 2026-04-03 14:45:07
sintesi: >
  Visualizzare oggetti complessi (es. Money, Coordinate, Entità) nei form richiede conversioni bidirezionali. Annotando i campi del DTO con @DateTimeFormat o @NumberFormat, Thymeleaf delega automaticamente la formattazione al sistema di conversione di 
tech: "thymeleaf"
tags: ["thymeleaf", "spring integration & flow archi"]
pdf_file: "type-conversion-formatter-system.pdf"
---

## Esigenza Reale
Gestire input di date e valute in form internazionali senza scrivere logica di parsing manuale per ogni richiesta.

## Analisi Tecnica
Problema: Errori di binding (400 Bad Request) dovuti a formati stringa non corrispondenti ai tipi Java del modello. Perché: Uso il sistema di conversione di Spring. Ho scelto di centralizzare le regole di formattazione nei Bean tramite annotazioni, permettendo a Thymeleaf di riflettere queste regole sia in lettura che in scrittura (binding).

## Esempio Implementativo

```thymeleaf
* Definisco il DTO con annotazioni di formattazione: Spring le usa per la
* conversione bidirezionale. */
 public class OrderFormDto 
{ @DateTimeFormat(pattern = "yyyy-MM-dd") 
// Input: "2026-03-25" -> LocalDate private LocalDate deliveryDate;
// @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME)
// Per datetime-local HTML5 private LocalDateTime scheduledAt;
// @NumberFormat(style = NumberFormat.Style.CURRENCY)
// Input: "€ 1.250,00" -> BigDecimal private BigDecimal totalAmount;
// @NumberFormat(pattern = "#,##0.00") private BigDecimal discountRate; private
// String customerName; }
 
/* Per tipi custom (es. Money, IBAN), implemento un Converter bidirezionale. */
 @Component public class MoneyConverter implements Converter<String, Money> 
{ @Override public Money convert(String source) 
{ 
// Parsing: "EUR 1250.00" -> Money(EUR, 1250.00) if (source == null ||
// source.isBlank()) return null; String[] parts = source.trim().split("\\s+",
// 2); return new Money(Currency.getInstance(parts[0]), new
// BigDecimal(parts[1])); }
 }
 @Component public class MoneyToStringConverter implements Converter<Money,
String>
{ @Override public String convert(Money source) 
{ 
// Formattazione: Money(EUR, 1250.00) -> "EUR 1250.00" return
// source.getCurrency().getCurrencyCode() + " " +
// source.getAmount().toPlainString(); }
 }
 
/* Registro i converter nel ConversionService di Spring: */
 @Configuration public class ConversionConfig implements WebMvcConfigurer 
{ @Autowired private MoneyConverter moneyConverter; @Autowired private
MoneyToStringConverter moneyToStringConverter; @Override public void
addFormatters(FormatterRegistry registry)
{ registry.addConverter(moneyConverter);
registry.addConverter(moneyToStringConverter);
// Per tipi Locale-aware, registro un Formatter (combina Printer + Parser)
// registry.addFormatter(new CoordinateFormatter()); }
 }
 
/* Formatter per Coordinate con supporto Locale: */
 public class CoordinateFormatter implements Formatter<GeoCoordinate> 
{ @Override public GeoCoordinate parse(String text, Locale locale) throws
ParseException
{ 
// "45.4654219,9.1859243" -> GeoCoordinate(lat, lon) String[] parts =
// text.split(","); return new
// GeoCoordinate(Double.parseDouble(parts[0].trim()),
// Double.parseDouble(parts[1].trim())); }
 @Override public String print(GeoCoordinate coord, Locale locale) 
{ return String.format(locale, "%.7f,%.7f", coord.getLat(), coord.getLon()); }
 }
 
* Controller: il binding avviene automaticamente senza codice di conversione
* manuale. */
 @PostMapping("/orders") public String createOrder(@ModelAttribute @Valid
OrderFormDto form, BindingResult result, Model model)
{ if (result.hasErrors()) 
{ return "orders/new"; }
 orderService.create(form); return "redirect:/orders"; }
 <!-- Template: th:field usa il ConversionService per formattare il valore
esistente e per fare il binding all'invio. --> <form th:object="$
{orderFormDto}
" th:action="@
{/orders}
" method="post"> <!-- th:field chiama print(deliveryDate, locale) per
visualizzare e parse() al submit --> <input type="date" th:field="*
{deliveryDate}
" class="form-control"> <!-- Input valuta: visualizza "€ 1.250,00" e parsifica
al submit --> <input type="text" th:field="*
{totalAmount}
" class="form-control" placeholder="€ 0,00"> <!-- Coordinate custom con
Formatter registrato --> <input type="text" th:field="*
{deliveryCoordinate}
" class="form-control" placeholder="45.4654,9.1859"> <button
type="submit">Conferma Ordine</button> </form>
```
