---
layout: post
title: Component-Based Architecture (Fragment Parameters)
date: '2026-03-31 16:25:01 '
sintesi: Passare dati semplici ai frammenti non permette di creare componenti veramente
  isolati. Passando interi oggetti, classi CSS e fallback ai frammenti, e usando il
  no-op token _, è possibile definire un valore predefinito nel mockup HTML che viene
  mante
esigenza: Creare un componente "Button" o "Card" universale che accetta varianti di
  colore, icone e label senza riscrivere l'HTML.
tech: thymeleaf
tags:
- thymeleaf
- advanced layout & templating
codice: '<!-- DEFINIZIONE DEL COMPONENTE: fragments/components.html --> <!-- Il componente
  Button accetta label, variant, icon e disabled come parametri. Il token _ come valore
  default garantisce che il template sia apribile nel browser senza server: il designer
  vede "Salva" con classe "btn-primary". --> <div th:fragment="button(label, variant,
  icon, disabled)" th:remove="tag"> <button th:type="''button''" th:class="''btn btn-''
  + ${variant ?: ''primary''}" th:disabled="${disabled ?: false}" th:attr="aria-label=${label
  ?: ''Azione''}"> <!-- Icona opzionale: se icon è _ o null, il tag span non viene
  renderizzato --> <span th:if="${icon != null and icon != _}" th:class="''icon icon-''
  + ${icon}"></span> <span th:text="${label ?: ''Salva''}">Salva</span> </button>
  </div> <!-- COMPONENTE Card con parametri multipli e contenuto innestato --> <div
  th:fragment="card(title, subtitle, cssClass, collapsible)" th:class="''card '' +
  ${cssClass ?: ''''}" th:remove="tag"> <div class="card-header"> <h5 class="card-title"
  th:text="${title ?: ''Titolo Card''}">Titolo Card</h5> <p th:if="${subtitle != null
  and subtitle != _}" class="card-subtitle" th:text="${subtitle}">Sottotitolo</p>
  <!-- Pulsante collapse: visibile solo se collapsible=true --> <button th:if="${collapsible
  ?: false}" class="btn btn-sm btn-outline-secondary" data-bs-toggle="collapse" th:attr="data-bs-target=''#card-body-''
  + ${#ids.seq(''card'')}"> Comprimi </button> </div> <div class="card-body"> <!--
  Layout placeholder (slot): il contenuto viene iniettato dal chiamante --> <th:block
  th:replace="~{::card-content}"> <p>Contenuto di default visibile nel browser senza
  server.</p> </th:block> </div> </div> <!-- UTILIZZO DEI COMPONENTI nel template
  pagina: --> <!-- Button con tutti i parametri --> <th:block th:replace="~{fragments/components
  :: button(''Elimina'', ''danger'', ''trash'', false)}"></th:block> <!-- Button con
  solo label: gli altri parametri usano il default --> <th:block th:replace="~{fragments/components
  :: button(''Salva'', _, _, _)}"></th:block> <!-- Card completa con contenuto iniettato
  --> <th:block th:replace="~{fragments/components :: card(''Ordini Recenti'', ''Ultimi
  30 giorni'', ''shadow-sm'', true)}"> <th:block th:fragment="card-content"> <table
  class="table"> <tr th:each="order : ${orders}"> <td th:text="${order.id}">ID</td>
  <td th:text="${order.total}">Totale</td> </tr> </table> </th:block> </th:block>'
---

Problema: Frammenti troppo rigidi che forzano a passare parametri vuoti o nulli, rendendo il codice verboso. Perché: Uso i parametri con default. Ho scelto il token _ per permettere al designer di vedere un'anteprima statica pur lasciando al programmatore il controllo dinamico totale.