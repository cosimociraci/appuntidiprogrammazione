---
layout: post
title: "Decoupled Logic (th:ref)"
date: 2026-03-31 19:21:45 
sintesi: "Mantenere i file HTML puri per i designer, separando la logica Thymeleaf in file .th.xml, permette ai grafici di lavorare su file HTML standard senza vedere attributi th:, mentre il server applica la logica di binding esternamente. I selettori CSS de"
tech: thymeleaf
tags: [thymeleaf, "custom dialects & processors"]
pdf_file: "decoupled-logic-thref.pdf"
---

## Esigenza Reale
Permettere a un team di designer esterni di aggiornare il layout HTML senza che debbano conoscere la sintassi di Thymeleaf.

## Analisi Tecnica
Problema: I file di template diventano illeggibili per i tool di design a causa dell'eccessiva presenza di attributi logici. Perché: Uso il Decoupled Template Logic. Ho scelto di spostare gli attributi th:text e th:each in un file XML parallelo per mantenere il file HTML visualizzabile in un normale browser senza server.

## Esempio Implementativo

```java
/* STRUTTURA DEL PROGETTO con Decoupled Logic: src/main/resources/templates/ ├──
* user-profile.html (HTML puro: il designer lo modifica liberamente) └── user-
* profile.th.xml (Logica Thymeleaf: separata dall'HTML) */
/* FILE: user-profile.html (HTML puro, visualizzabile in qualsiasi browser) */
// <!DOCTYPE html> // <html> // <head><title>Profilo Utente</title></head> //
<body> //   <div id="user-card"> //     <img id="user-avatar"
src="/img/placeholder.png" alt="Avatar"> //     <h1 id="user-name">Nome
Cognome</h1> //     <span id="user-role" class="badge badge-
primary">Ruolo</span> //     <p id="user-bio">Biografia dell'utente
placeholder...</p> //     <ul id="order-list"> //       <li class="order-item">
//         <span class="order-id">#00001</span> //         <span class="order-
date">01/01/2026</span> //         <span class="order-total">€ 100,00</span> //
</li> //     </ul> //     <div id="no-orders" style="display:none"> //
<p>Nessun ordine presente</p> //     </div> //   </div> // </body> // </html> /*
FILE: user-profile.th.xml (Logica Thymeleaf separata: usa selettori CSS per
riferirsi agli elementi HTML) */ // <?xml version="1.0"?> // <thlogic> //   <!--
Seleziono l'elemento tramite id CSS e applico th:src e th:alt --> //   <attr
sel="#user-avatar" th:src="@{'/api/users/' + ${user.id} + '/avatar'}"
th:alt="${user.name}" /> //   //   <!-- Binding del testo: il designer vede
"Nome Cognome", il server inietta il valore reale --> //   <attr sel="#user-
name" th:text="${user.fullName}" /> //   //   <!-- Classe CSS dinamica basata
sul ruolo --> //   <attr sel="#user-role" th:text="${user.role}"
th:class="'badge ' + ${user.roleBadgeClass}" /> //   //   <!-- Testo con
formattazione da Expression Object custom --> //   <attr sel="#user-bio"
th:text="${#strUtils.truncate(user.bio, 300)}" /> //   //   <!-- Iterazione
sulla lista ordini: replico il primo li per ogni ordine --> //   <attr
sel="#order-list/li" th:each="order : ${user.recentOrders}" > //     <attr
sel=".order-id" th:text="'#' + ${order.id}" /> //     <attr sel=".order-date"
th:text="${#temporals.format(order.date, 'dd/MM/yyyy')}" /> //     <attr
sel=".order-total" th:text="${#finance.formatCurrency(order.total, 'EUR')}" />
//   </attr> //   //   <!-- Mostra il messaggio se la lista è vuota --> //
<attr sel="#no-orders" th:if="${user.recentOrders.isEmpty()}" /> // </thlogic>
/* Abilito il Decoupled Logic in Spring Boot configurando il resolver: */
@Configuration public class ThymeleafDecoupledConfig { @Bean public
SpringResourceTemplateResolver templateResolver() {
SpringResourceTemplateResolver resolver = new SpringResourceTemplateResolver();
resolver.setPrefix("classpath:/templates/"); resolver.setSuffix(".html");
resolver.setTemplateMode(TemplateMode.HTML);
resolver.setUseDecoupledLogic(true); // Abilito la lettura del file .th.xml
parallelo resolver.setCacheable(false); // Disabilito in sviluppo return
resolver; } } /* Il controller rimane invariato: non sa nulla della separazione
HTML/XML. */ @GetMapping("/profile/{id}") public String
userProfile(@PathVariable Long id, Model model) { model.addAttribute("user",
userService.findById(id)); return "user-profile"; // Thymeleaf carica
automaticamente user-profile.html + user-profile.th.xml }
```
