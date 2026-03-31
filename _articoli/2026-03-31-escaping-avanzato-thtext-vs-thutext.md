---
layout: post
title: "Escaping Avanzato: th:text vs th:utext"
date: 2026-03-31 19:00:34 
sintesi: "L'uso di th:utext (unescaped) per renderizzare contenuti HTML salvati nel DB è la causa principale di XSS. Prima di passare una stringa HTML alla view, questa deve essere processata nel Service layer con un parser come OWASP Java HTML Sanitizer per r"
tech: thymeleaf
tags: [thymeleaf, "security & spel expressions"]
pdf_file: "escaping-avanzato-thtext-vs-thutext.pdf"
---

## Esigenza Reale
Visualizzare correttamente descrizioni formattate (RTF) inserite dagli utenti senza esporsi a iniezioni di script.

## Analisi Tecnica
Problema: Iniezione di JavaScript malevolo che viene eseguito nel browser di altri utenti quando visualizzano contenuti non filtrati. Perché: Sanitizzazione "White-list". Ho scelto di pulire il markup a livello di backend prima di inviarlo al modello, garantendo che solo i tag HTML sicuri (b, i, p) arrivino al motore di rendering.

## Esempio Implementativo

```thymeleaf
/* Aggiungo OWASP Java HTML Sanitizer al pom.xml: */ //
<dependency>
    // <groupId>com.googlecode.owasp-java-html-sanitizer</groupId> //
    <artifactId>owasp-java-html-sanitizer</artifactId> // <version>20220608.1</version> //
</dependency>
/* Definisco le policy di sanitizzazione per diversi contesti di utilizzo. */ @Configuration public
class HtmlSanitizerConfig { /* Policy per commenti e descrizioni utente: solo formattazione base. */
@Bean("basicHtmlPolicy") public PolicyFactory basicHtmlPolicy() { return new HtmlPolicyBuilder()
.allowElements("b", "i", "em", "strong", "u", "s", "br", "p") // Nessun tag strutturale, nessun
link, nessuna immagine .toFactory(); } /* Policy per articoli del CMS: formattazione ricca ma senza
JS. */ @Bean("richHtmlPolicy") public PolicyFactory richHtmlPolicy() { return new
HtmlPolicyBuilder() .allowElements("b", "i", "em", "strong", "u", "s", "br", "p", "h2", "h3", "h4",
"ul", "ol", "li", "blockquote", "code", "pre") .allowElements("a") .onElements("a")
.allowAttributes("href").matching(Pattern.compile("https?://.*")) // Solo URL assoluti HTTPS
.allowAttributes("target").matching(Pattern.compile("_blank")).onElements("a")
.requireRelNofollowOnLinks() // Aggiunge rel="nofollow" automaticamente .allowElements("img")
.onElements("img") .allowAttributes("src").matching(Pattern.compile("https://.*")) // Solo immagini
HTTPS .allowAttributes("alt", "width", "height").onElements("img") .toFactory(); } } /* Service che
applica la sanitizzazione prima che il dato raggiunga il modello. */ @Service public class
ContentSanitizationService { @Autowired @Qualifier("basicHtmlPolicy") private PolicyFactory
basicHtmlPolicy; @Autowired @Qualifier("richHtmlPolicy") private PolicyFactory richHtmlPolicy; /*
Sanitizzazione di base per commenti e bio utente. */ public String sanitizeBasic(String userInput) {
if (userInput == null) return ""; return basicHtmlPolicy.sanitize(userInput); } /* Sanitizzazione
ricca per articoli del CMS. */ public String sanitizeRich(String cmsContent) { if (cmsContent ==
null) return ""; return richHtmlPolicy.sanitize(cmsContent); } /* Sanitizzazione per output JSON
(prevenzione XSS in API REST): */ public String sanitizeForJson(String input) { if (input == null)
return null; // Escape caratteri pericolosi in contesti JSON return input.replace("<",
"\\u003C").replace(">", "\\u003E").replace("&", "\\u0026"); } } /* Controller che usa la
sanitizzazione prima di passare i dati al modello: */ @Controller public class ArticleController {
@Autowired private ContentSanitizationService sanitizer; @Autowired private ArticleRepository
articleRepository; @GetMapping("/articles/{id}") public String showArticle(@PathVariable Long id,
Model model) { Article article = articleRepository.findById(id).orElseThrow(); // Sanitizzo nel
controller: il modello contiene solo HTML sicuro model.addAttribute("title", article.getTitle()); //
th:text: escaped automaticamente model.addAttribute("safeBody",
sanitizer.sanitizeRich(article.getBody())); // th:utext: sicuro perché già sanitizzato
model.addAttribute("safeExcerpt", sanitizer.sanitizeBasic(article.getExcerpt())); return
"articles/show"; } }
<!-- Template: th:utext è sicuro perché i dati sono già stati sanitizzati nel Service. -->
<!-- th:text per contenuto plain text: Thymeleaf fa l'escaping automaticamente -->
<h1 th:text="${title}">Titolo Articolo</h1>
<!-- th:utext SOLO per contenuto pre-sanitizzato: il commento documenta la scelta -->
<!-- safeBody è stato passato attraverso richHtmlPolicy: nessun tag script possibile -->
<div th:utext="${safeBody}">Corpo dell'articolo...</div>
<!-- th:utext per excerpt pre-sanitizzato con basicHtmlPolicy -->
<p th:utext="${safeExcerpt}">Anteprima...</p>

```
