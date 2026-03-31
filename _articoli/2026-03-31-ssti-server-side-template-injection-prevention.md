---
layout: post
title: "SSTI (Server-Side Template Injection) Prevention"
date: 2026-03-31 19:00:33 
sintesi: "Una vulnerabilità storica di Thymeleaf permette l'esecuzione di codice se il nome della vista è costruito con input utente. Concatenare parametri della request nel percorso della view (return user/ + lang + /index) è pericoloso. È necessario usare un"
tech: thymeleaf
tags: [thymeleaf, "security & spel expressions"]
pdf_file: "ssti-server-side-template-injection-prevention.pdf"
---

## Esigenza Reale
Blindare i controller che gestiscono percorsi dinamici o temi grafici selezionabili dall'utente.

## Analisi Tecnica
Problema: Esecuzione di codice remoto (RCE) tramite la manipolazione dei parametri che determinano quale file di template deve essere renderizzato. Perché: Sanitizzazione rigorosa dei path. Ho scelto di mappare gli input utente su una Enum predefinita prima di restituire il nome della stringa al DispatcherServlet.

## Esempio Implementativo

```thymeleaf
/* Dimostro l'attacco SSTI su Thymeleaf per capire cosa stiamo prevenendo. Un attaccante invia: GET
/page?lang=__$%7BT(java.lang.Runtime).getRuntime().exec('id')%7D__::.x Thymeleaf interpreta la
sequenza __${...}__:: come preprocessing e valuta l'espressione, eseguendo comandi di sistema con i
privilegi della JVM. */ // CODICE VULNERABILE: concatenazione diretta di input utente nel nome della
view @GetMapping("/page") public String VULNERABLE_render(@RequestParam String lang, Model model) {
return "pages/" + lang + "/index"; // VULNERABILE: lang = "../../../etc/passwd" o payload SSTI } /*
SOLUZIONE 1: Allow-list tramite Enum. Solo le viste esplicitamente definite nell'Enum possono essere
caricate. Qualsiasi input non riconosciuto viene rifiutato con un errore controllato. */ public enum
AllowedPage { HOME("pages/home/index"), ABOUT("pages/about/index"), CONTACT("pages/contact/index"),
IT("pages/it/index"), EN("pages/en/index"), DE("pages/de/index"); private final String templatePath;
AllowedPage(String templatePath) { this.templatePath = templatePath; } public String
getTemplatePath() { return templatePath; } public static Optional<AllowedPage>
    fromCode(String code) { return Arrays.stream(values()) .filter(p ->
    p.name().equalsIgnoreCase(code)) .findFirst(); } } @GetMapping("/page") public String
    safeRender(@RequestParam String code, Model model) { // Mapping sicuro: solo valori nell'Enum
    passano al motore Thymeleaf AllowedPage page = AllowedPage.fromCode(code) .orElseThrow(() -> new
    ResponseStatusException(HttpStatus.BAD_REQUEST, "Pagina non riconosciuta: " + code));
    model.addAttribute("pageCode", page.name()); return page.getTemplatePath(); // Percorso
    hardcoded nell'Enum: zero input utente nel path } /* SOLUZIONE 2: Allow-list tramite Map statica
    per logiche più dinamiche. */ @Controller public class ThemeController { // Mappa statica: i
    percorsi sono hardcoded, l'utente sceglie solo la chiave private static final Map<String,
        String
    >
        ALLOWED_THEMES = Map.of( "light", "themes/light/index", "dark", "themes/dark/index",
        "high-contrast", "themes/high-contrast/index" ); @GetMapping("/theme") public String
        renderTheme(@RequestParam String theme, Model model) { String templatePath =
        ALLOWED_THEMES.get(theme); if (templatePath == null) { log.warn("Tentativo di accesso a tema
        non autorizzato: '{}' da IP: {}", theme, request.getRemoteAddr()); return "error/400"; //
        Pagina di errore predefinita } return templatePath; } } /* SOLUZIONE 3: Per
        l'internazionalizzazione, uso LocaleChangeInterceptor di Spring invece di costruire percorsi
        manualmente. */ @Configuration public class WebMvcConfig implements WebMvcConfigurer { @Bean
        public LocaleChangeInterceptor localeChangeInterceptor() { LocaleChangeInterceptor
        interceptor = new LocaleChangeInterceptor(); interceptor.setParamName("lang"); // Spring
        gestisce il cambio locale in modo sicuro return interceptor; } @Override public void
        addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(localeChangeInterceptor()); } } /* Con LocaleChangeInterceptor, il
        controller non tocca mai il parametro lang: */ @GetMapping("/page") public String
        safePage(Model model) { // Thymeleaf usa il Locale corrente per #messages: zero
        manipolazione del path return "pages/index"; // Percorso fisso: Spring risolve l'i18n dai
        messaggi }</String,
    ></AllowedPage
>

```
