---
layout: post
title: "Post-Redirect-Get (PRG) & Flash Attributes"
date: 2026-03-31 16:39:58 
tech: thymeleaf
tags: ['thymeleaf', 'spring integration & flow archi']
pdf_file: "post-redirect-get-prg-flash-attributes.pdf"
---

## Esigenza Reale
Evitare la duplicazione di transazioni e gestire notifiche utente "one-shot" dopo operazioni di scrittura (POST).

## Analisi Tecnica
Problema: Perdita dei messaggi di feedback utente dopo un redirect o esecuzione multipla accidentale di azioni lato server. Perché: Implemento il pattern PRG con Flash Scope. Ho scelto questa strategia per separare nettamente le azioni di modifica dello stato dalle azioni di visualizzazione, migliorando l'esperienza utente e la coerenza dei dati.

## Esempio Implementativo

```thymeleaf
/* Controller che implementa PRG con Flash Attributes strutturati. */ @Controller @RequestMapping("/orders") public class OrderController { @PostMapping public String createOrder( @ModelAttribute @Valid OrderFormDto form, BindingResult result, Model model, RedirectAttributes redirectAttrs) { if (result.hasErrors()) { // NON faccio redirect in caso di errori: devo mostrare i campi valorizzati model.addAttribute("orderFormDto", form); return "orders/new"; // Rendering diretto, no redirect } try { Order created = orderService.create(form); // Flash attribute strutturato: sopravvive a UN solo redirect, poi viene eliminato // Uso un oggetto FlashMessage per supportare tipi diversi (success, warning, error) redirectAttrs.addFlashAttribute("flashMessage", new FlashMessage( FlashMessage.Type.SUCCESS, "Ordine #" + created.getId() + " creato con successo!", "/orders/" + created.getId() // Link opzionale per azione successiva )); return "redirect:/orders/" + created.getId(); } catch (InsufficientStockException e) { redirectAttrs.addFlashAttribute("flashMessage", new FlashMessage(FlashMessage.Type.WARNING, "Stock insufficiente per: " + e.getProductName())); return "redirect:/orders/new"; } catch (Exception e) { log.error("Errore creazione ordine", e); redirectAttrs.addFlashAttribute("flashMessage", new FlashMessage(FlashMessage.Type.ERROR, "Errore imprevisto. Riprova più tardi.")); return "redirect:/orders/new"; } } @PostMapping("/{id}/delete") public String deleteOrder(@PathVariable Long id, RedirectAttributes redirectAttrs) { orderService.delete(id); redirectAttrs.addFlashAttribute("flashMessage", new FlashMessage(FlashMessage.Type.SUCCESS, "Ordine #" + id + " eliminato.")); // Redirect alla lista: il browser vede GET /orders, refresh sicuro return "redirect:/orders"; } } /* FlashMessage: oggetto tipizzato per messaggi con varianti visive. */ public record FlashMessage(Type type, String text, String actionUrl) { public FlashMessage(Type type, String text) { this(type, text, null); } public String getCssClass() { return switch (type) { case SUCCESS -> "alert-success"; case WARNING -> "alert-warning"; case ERROR -> "alert-danger"; case INFO -> "alert-info"; }; } public enum Type { SUCCESS, WARNING, ERROR, INFO } } <!-- Frammento riutilizzabile per i flash message: incluso nel layout base. Thymeleaf lo trova automaticamente nel model dopo il redirect perché Spring lo copia dalla sessione flash. --> <!-- fragments/flash-message.html --> <div th:fragment="flash-alert" th:if="${flashMessage != null}" th:class="'alert ' + ${flashMessage.cssClass} + ' alert-dismissible fade show'" role="alert"> <span th:text="${flashMessage.text}">Messaggio</span> <!-- Link opzionale all'azione successiva --> <a th:if="${flashMessage.actionUrl != null}" th:href="${flashMessage.actionUrl}" class="alert-link ms-2">Visualizza</a> <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Chiudi"></button> </div> <!-- Nel layout base: il frammento è presente in tutte le pagine. --> <!-- <th:block th:replace="~{fragments/flash-message :: flash-alert}"></th:block> -->
```
