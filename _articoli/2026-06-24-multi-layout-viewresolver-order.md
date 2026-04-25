---
layout: code
title: "Multi-Layout ViewResolver Order"
date: 2026-06-24 12:00:00
sintesi: >
  In progetti grandi convivono spesso diverse tecnologie (Thymeleaf per il frontend, JSP per il legacy, JSON per API). Configurando correttamente la proprietà order del ViewResolver, Spring sa quale motore interpellare per primo. Questo permette una mi
tech: "java"
tags: ["java", "thymeleaf", "pattern matching", "garbage collector", "spring boot"]
pdf_file: "multi-layout-viewresolver-order.pdf"
---

## Esigenza Reale
Integrare nuovi moduli Thymeleaf in una vecchia applicazione Enterprise che usa ancora tecnologie di templating legacy.

## Analisi Tecnica
**Problema:** Conflitti tra motori di template diversi che tentano di risolvere la stessa vista, causando errori di "Template Not Found".

**Perché:** Configuro la catena dei ViewResolver. Ho scelto di assegnare indici di priorità espliciti per garantire che il DispatcherServlet trovi sempre il renderer corretto nel minor tempo possibile.

## Esempio Implementativo

```java
/* Disabilito la auto-configurazione di Thymeleaf per prendere il controllo
    completo della chain. */
@SpringBootApplication(exclude = {
    ThymeleafAutoConfiguration.class
}
) public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
/* Configuro la catena completa di ViewResolver con ordine di priorità
    esplicito. */
@Configuration public class ViewResolverConfig {
    /* 1. ContentNegotiatingViewResolver: smista in base al Content-Type della
        richiesta. Priorità assoluta: gestisce le richieste API (JSON/XML) prima
        di qualsiasi motore di template. */
    @Bean public ContentNegotiatingViewResolver contentNegotiatingViewResolver(
        List<ViewResolver> resolvers, List<HttpMessageConverter<?>> converters)
        {
        ContentNegotiatingViewResolver cnvr = new
            ContentNegotiatingViewResolver();
        // Le richieste con Accept: application/json vanno a Jackson
            direttamente // Le richieste con Accept: text/html vanno ai template
            engine
        return cnvr;
    }
    /* 2. ThymeleafViewResolver: gestisce i file .html (order=1: alta priorità
        tra i template engine). */
    @Bean public ThymeleafViewResolver
        thymeleafViewResolver(SpringTemplateEngine engine) {
        ThymeleafViewResolver resolver = new ThymeleafViewResolver();
        resolver.setTemplateEngine(engine);
        resolver.setOrder(1);
        // Prima scelta per le view resolver.setCharacterEncoding("UTF-8")
        ;
        // Thymeleaf gestisce SOLO i template .html: passa agli altri per .jsp e
            .vm resolver.setViewNames(new String[]
        {
            "*.html", "thymeleaf
            /*"}); // Pattern inclusione // Oppure esclusione esplicita dei
                suffissi legacy: // resolver.setExcludedViewNames(new
                String[]{"*.jsp", "*.jspx"}); resolver.setCache(true); //
                Obbligatorio in produzione return resolver; } /* 3.
                InternalResourceViewResolver: gestisce i file JSP legacy
                (order=2: fallback). */
            @Bean public InternalResourceViewResolver jspViewResolver() {
                InternalResourceViewResolver resolver = new
                    InternalResourceViewResolver();
                resolver.setPrefix("/WEB-INF/jsp/");
                resolver.setSuffix(".jsp");
                resolver.setOrder(2);
                // Secondo nella catena: usato solo se Thymeleaf non trova la
                    vista
                return resolver;
            }
            /* 4. FreeMarkerViewResolver: per template legacy
                Velocity/FreeMarker (order=3: ultima risorsa). */
            @Bean public FreeMarkerViewResolver freeMarkerViewResolver() {
                FreeMarkerViewResolver resolver = new FreeMarkerViewResolver();
                resolver.setSuffix(".ftl");
                resolver.setOrder(3);
                return resolver;
            }
        }
        /* Configuro il TemplateResolver di Thymeleaf per risolvere SOLO da
            /templates: */
        @Bean public SpringResourceTemplateResolver thymeleafTemplateResolver()
            {
            SpringResourceTemplateResolver resolver = new
                SpringResourceTemplateResolver();
            resolver.setPrefix("classpath:/templates/");
            resolver.setSuffix(".html");
            resolver.setTemplateMode(TemplateMode.HTML);
            resolver.setCacheable(true);
            // Thymeleaf lancia TemplateInputException se il file non esiste: //
                il ContentNegotiatingViewResolver lo intercetta e passa al
                resolver successivo resolver.setCheckExistence(true)
            ;
            // Fondamentale per la coesistenza
            return resolver;
        }
        /* Controller che dimostra la coesistenza: la stessa URL risponde con
            template diversi. */
        @Controller
        @RequestMapping("/reports") public class ReportController {
            @GetMapping("/summary") public String summary(Model model) {
                model.addAttribute("data", reportService.getSummary());
                return "reports/summary";
                // Risolto da Thymeleaf: /templates/reports/summary.html
            }
            @GetMapping("/legacy-detail") public String legacyDetail(Model
                model) {
                model.addAttribute("data", reportService.getDetail());
                return "reports/detail";
                // NON trovato da Thymeleaf -> passa a JSP:
                    /WEB-INF/jsp/reports/detail.jsp
            }
            /* Migrazione graduale: richieste API esistenti non cambiano
                comportamento. */
            @GetMapping(value = "/api/summary", produces =
                MediaType.APPLICATION_JSON_VALUE)
            @ResponseBody public ReportSummaryDto apiSummary() {
                return reportService.getSummaryDto();
                // JSON via Jackson: ContentNegotiating lo gestisce prima dei
                    template
            }
        }
```
