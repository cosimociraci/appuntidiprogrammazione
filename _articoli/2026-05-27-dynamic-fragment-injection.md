---
layout: post
title: "Dynamic Fragment Injection"
date: 2026-05-27 12:00:00
sintesi: >
  A volte non si sa quale frammento caricare finché non si è a runtime (es. blocchi di un CMS). L'espressione ~{${path} :: ${name}} permette a Thymeleaf di risolvere prima le stringhe dentro ${} e poi cercare il frammento. Questo permette di implementa
tech: "java"
tags: ["thymeleaf", "advanced layout & templating"]
pdf_file: "dynamic-fragment-injection.pdf"
---

## Esigenza Reale
Implementare un sistema di dashboard dove ogni utente può aggiungere "Widget" diversi caricati dinamicamente.

## Analisi Tecnica
**Problema:** Necessità di gestire decine di th:if per decidere quale frammento mostrare, creando template illeggibili.
**Perché:** Uso il caricamento dinamico per nome. Ho scelto di mappare i nomi dei frammenti nel database per rendere l'interfaccia estensibile senza modificare il codice Java dei controller.

## Esempio Implementativo

```java
/* Controller: recupero la configurazione della dashboard dal DB e la passo al
    template. */
@GetMapping("/dashboard") public String dashboard(Model model,
@AuthenticationPrincipal UserDetails user) {
    // Recupero i widget configurati per questo utente: ogni widget ha un tipo e
        parametri List<WidgetConfig> widgets =
        dashboardService.getWidgetsForUser(user.getUsername())
    ;
    model.addAttribute("widgets", widgets);
    return "dashboard";
}
/* WidgetConfig: definisce il tipo e i dati del widget. */
public record WidgetConfig( String type,
// Es: "sales-chart", "user-stats", "alert-banner" String title, Map<String,
    Object> params // Parametri specifici per tipo )
{
}
/* Nel service: carico i dati specifici per ogni tipo di widget. */
@Service public class DashboardService {
    public List<WidgetConfig> getWidgetsForUser(String username) {
        List<UserWidget> dbWidgets = widgetRepository.findByUsername(username);
        return dbWidgets.stream() .map(w -> new WidgetConfig( w.getType(),
            w.getTitle(), loadWidgetData(w.getType(), w.getParams()) ))
            .collect(Collectors.toList());
    }
    private Map<String, Object> loadWidgetData(String type, Map<String, String>
        params) {
        return switch (type) {
            case "sales-chart" -> Map.of("data", salesService.getLast30Days());
            case "user-stats" -> Map.of("stats", userService.getStats());
            case "alert-banner" -> Map.of("alerts", alertService.getActive());
            default -> Collections.emptyMap();
        }
        ;
    }
}
<!-- Template dashboard.html: un solo th:each gestisce tutti i tipi di widget.
    --> <!-- Il path del frammento viene costruito dinamicamente: zero th:if -->
    <!-- struttura directory: templates/widgets/sales-chart.html,
    user-stats.html, alert-banner.html --> <div class="dashboard-grid"> <div
    th:each="widget : ${
    widgets
}
" class="widget-container"> <!-- Iniezione dinamica: Thymeleaf risolve
    'widgets/' + widget.type prima di cercare il frammento. Se il frammento non
    esiste, Thymeleaf lancia un errore: gestisco con th:if preventivo. --> <div
    th:if="${
    @widgetRegistry.exists(widget.type)
}
" th:insert="~{
    'widgets/' + ${
        widget.type
    }
    + ' :: content(title=${
        widget.title
    }
    , params=${
        widget.params
    }
    )'
}
"> </div> <!-- Fallback per widget sconosciuti --> <div th:unless="${
    @widgetRegistry.exists(widget.type)
}
" class="alert alert-warning"> Widget non riconosciuto: <strong th:text="${
    widget.type
}
">tipo</strong> </div> </div> </div> <!-- Template widgets/sales-chart.html: -->
    <!-- <div th:fragment="content(title, params)" class="widget-sales-chart">
    --> <!-- <h4 th:text="${
    title
}
">Vendite</h4> --> <!-- <canvas th:id="${
    'chart-' + #ids.seq('chart')
}
" --> <!-- th:attr="data-values=${
    params.data
}
"></canvas> --> <!-- </div> -->
/* WidgetRegistry: verifica l'esistenza del template prima del rendering. */
@Component public class WidgetRegistry {
    @Autowired private TemplateEngine templateEngine;
    public boolean exists(String widgetType) {
        try {
            templateEngine.getConfiguration().getTemplateManager()
                .parseStandalone(new EngineConfiguration(), "widgets/" +
                widgetType, null, TemplateMode.HTML, false, null);
            return true;
        }
        catch (TemplateInputException e) {
            return false;
        }
    }
}
```
