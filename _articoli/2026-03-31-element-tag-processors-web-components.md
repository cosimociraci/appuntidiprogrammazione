---
layout: post
title: "Element Tag Processors (Web Components)"
date: 2026-03-31 19:00:29 
sintesi: "Sostituire interi tag custom (es. <app:navbar>) con markup generato lato server permette di incapsulare logiche di navigazione complesse che appaiono come semplici tag nel file HTML. IElementTagProcessor, combinato con IModelFactory, permette di cost"
tech: thymeleaf
tags: [thymeleaf, "custom dialects & processors"]
pdf_file: "element-tag-processors-web-components.pdf"
---

## Esigenza Reale
Implementare un sistema di menu dinamico che si auto-genera leggendo le rotte di Spring Security.

## Analisi Tecnica
Problema: Markup del menu di navigazione enorme e difficile da manutenere se copiato in ogni pagina. Perché: Uso la manipolazione del modello (IModel). Ho scelto di generare il codice HTML del menu lato server così da poter cambiare la struttura in un unico punto del codice Java.

## Esempio Implementativo

```thymeleaf
/* Definisco un Element Tag Processor che trasforma
<app:navbar>
    in un menu dinamico basato sui permessi dell'utente corrente. */ public class NavbarTagProcessor
    extends AbstractElementTagProcessor { private static final String TAG_NAME = "navbar"; private
    static final int PRECEDENCE = 100; private final RouteRegistry routeRegistry; // Iniettato via
    costruttore public NavbarTagProcessor(String dialectPrefix, RouteRegistry routeRegistry) {
    super(TemplateMode.HTML, dialectPrefix, TAG_NAME, // Tag intercettato:
    <app:navbar>
        true, // Match del tag esatto null, false, PRECEDENCE); this.routeRegistry = routeRegistry;
        } @Override protected void doProcess( ITemplateContext context, IProcessableElementTag tag,
        IElementTagStructureHandler structureHandler) { // Recupero l'autenticazione corrente
        Authentication auth = SecurityContextHolder.getContext().getAuthentication(); // Recupero le
        voci di menu filtrate per ruolo List<NavItem>
            allowedItems = routeRegistry.getNavItems().stream() .filter(item ->
            item.getRoles().isEmpty() || item.getRoles().stream() .anyMatch(role ->
            auth.getAuthorities().stream() .anyMatch(a -> a.getAuthority().equals("ROLE_" + role))))
            .collect(Collectors.toList()); // Costruisco il modello HTML con IModelFactory
            IModelFactory modelFactory = context.getModelFactory(); IModel model =
            modelFactory.createModel(); //
            <nav class="navbar navbar-expand-lg">
                model.add(modelFactory.createOpenElementTag("nav", "class", "navbar navbar-expand-lg
                navbar-dark bg-dark")); model.add(modelFactory.createOpenElementTag("div", "class",
                "container-fluid")); // Logo model.add(modelFactory.createOpenElementTag("a",
                Map.of("class", "navbar-brand", "href", "/"), false));
                model.add(modelFactory.createText("MyApp"));
                model.add(modelFactory.createCloseElementTag("a")); // Menu items
                model.add(modelFactory.createOpenElementTag("ul", "class", "navbar-nav me-auto"));
                for (NavItem item : allowedItems) { Map<String, String>
                    liAttrs = new HashMap<>(); // Evidenzio la voce attiva confrontando con il
                    percorso corrente String currentPath = ((WebContext)
                    context).getRequest().getRequestURI(); if
                    (currentPath.startsWith(item.getPath())) { liAttrs.put("class", "nav-item
                    active"); } else { liAttrs.put("class", "nav-item"); }
                    model.add(modelFactory.createOpenElementTag("li", liAttrs,
                    AttributeValueQuotes.DOUBLE, false));
                    model.add(modelFactory.createOpenElementTag("a", Map.of("class", "nav-link",
                    "href", item.getPath()), false));
                    model.add(modelFactory.createText(item.getLabel()));
                    model.add(modelFactory.createCloseElementTag("a"));
                    model.add(modelFactory.createCloseElementTag("li")); }
                    model.add(modelFactory.createCloseElementTag("ul"));
                    model.add(modelFactory.createCloseElementTag("div"));
                    model.add(modelFactory.createCloseElementTag("nav")); // Sostituisco il tag
                    <app:navbar>
                        con il markup generato structureHandler.replaceWith(model, true); } } /*
                        Registro il processore nel dialetto aziendale: */ @Override public
                        Set<IProcessor>
                            getProcessors(String dialectPrefix) { Set<IProcessor>
                                processors = new HashSet<>(); processors.add(new
                                NavbarTagProcessor(dialectPrefix, routeRegistry)); // ... altri
                                processori return processors; } /* Uso nel template base
                                layout.html: una sola riga invece di decine di righe di markup. */
                                // <!DOCTYPE html> //
                                <html xmlns:app="http://www.mycompany.com/thymeleaf">
                                    //
                                    <body>
                                        // <app:navbar></app:navbar>
                                        <!-- Generato dinamicamente con voci filtrate per ruolo -->
                                        //
                                        <div th:replace="~{::content}"></div>
                                        //
                                    </body>
                                    //
                                </html></IProcessor
                            ></IProcessor
                        ></app:navbar
                    ></String,
                >
            </nav></NavItem
        ></app:navbar
    ></app:navbar
>

```
