---
layout: post
title: "Expression Objects Custom"
date: 2026-03-31 18:54:45 
sintesi: "Spesso servono utility nel template (formattazione date particolari, calcoli finanziari) che non appartengono al modello dati. Registrando oggetti tramite IExpressionObjectFactory, è possibile richiamarli con la sintassi ${#myUtils...}, simile ai bui"
tech: thymeleaf
tags: [thymeleaf, "custom dialects & processors"]
pdf_file: "expression-objects-custom.pdf"
---

## Esigenza Reale
Fornire ai designer un modo semplice per formattare valute o gestire traduzioni complesse direttamente nel template.

## Analisi Tecnica
Problema: Inserimento di logica di formattazione pesante nei Controller o nei DTO, violando la separazione delle responsabilità. Perché: Implemento un Expression Object. Ho scelto di creare un oggetto utility registrato nel dialetto per centralizzare le funzioni di supporto alla view.

## Esempio Implementativo

```thymeleaf
/* Definisco la classe utility con i metodi helper che voglio esporre ai template. */ public class
FinanceUtils { /* Formatta un importo con la valuta locale e gestisce i casi null. */ public String
formatCurrency(BigDecimal amount, String currencyCode) { if (amount == null) return "N/D";
NumberFormat formatter = NumberFormat.getCurrencyInstance(Locale.ITALY);
formatter.setCurrency(Currency.getInstance(currencyCode)); return formatter.format(amount); } /*
Calcola la percentuale con arrotondamento e gestione della divisione per zero. */ public String
formatPercentage(BigDecimal value, BigDecimal total) { if (total == null ||
total.compareTo(BigDecimal.ZERO) == 0) return "0%"; BigDecimal percentage = value.divide(total, 4,
RoundingMode.HALF_UP) .multiply(BigDecimal.valueOf(100)); return String.format("%.1f%%",
percentage); } /* Restituisce la classe CSS Bootstrap in base al segno del valore (per dashboard
finanziarie). */ public String trendClass(BigDecimal value) { if (value == null ||
value.compareTo(BigDecimal.ZERO) == 0) return "text-secondary"; return
value.compareTo(BigDecimal.ZERO) > 0 ? "text-success" : "text-danger"; } /* Tronca una stringa al
numero di caratteri specificato aggiungendo "..." se necessario. */ public String truncate(String
text, int maxLength) { if (text == null) return ""; return text.length() <= maxLength ? text :
text.substring(0, maxLength) + "..."; } } /* Implemento la factory che registra l'utility nel
contesto Thymeleaf. */ public class CompanyExpressionFactory implements IExpressionObjectFactory {
private static final String FINANCE_UTILS_NAME = "finance"; private static final String
STRING_UTILS_NAME = "strUtils"; private static final Set<String>
    NAMES = new HashSet<>(Arrays.asList(FINANCE_UTILS_NAME, STRING_UTILS_NAME)); @Override public
    Set<String>
        getAllExpressionObjectNames() { return NAMES; // Thymeleaf chiama questo metodo per sapere
        quali nomi sono disponibili } @Override public Object buildObject(IExpressionContext
        context, String expressionObjectName) { // Creo l'oggetto utility su richiesta: potrei usare
        un singleton per performance switch (expressionObjectName) { case FINANCE_UTILS_NAME: return
        new FinanceUtils(); case STRING_UTILS_NAME: return new StringUtils(); default: return null;
        } } @Override public boolean isCacheable(String expressionObjectName) { return true; //
        L'oggetto è stateless: posso cacharlo per tutta la richiesta } } /* Registro la factory nel
        dialetto aziendale aggiungendola al metodo getExpressionObjectFactory(): */ public class
        CompanyDialect implements IProcessorDialect { // ... altri metodi ... @Override public
        IExpressionObjectFactory getExpressionObjectFactory() { return new
        CompanyExpressionFactory(); } } /* Uso nei template: sintassi identica agli oggetti built-in
        di Thymeleaf. */ //
        <td th:class="${#finance.trendClass(order.profit)}">
            // <span th:text="${#finance.formatCurrency(order.total, 'EUR')}">€ 0,00</span> //
        </td>
        //
        <p th:text="${#finance.formatPercentage(product.sold, product.stock)}">0%</p>
        // <span th:text="${#strUtils.truncate(article.content, 150)}">Descrizione...</span></String
    ></String
>

```
