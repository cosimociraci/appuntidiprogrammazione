---
layout: post
title: Evitare il Reflection Stack con th:with
date: '2026-03-31 16:25:01 '
sintesi: Accedere ripetutamente a metodi complessi tramite SpEL all'interno di un
  ciclo è costoso. L'istruzione th:with crea una variabile locale nel contesto di
  Thymeleaf. Memorizzando il risultato di una computazione o di una lookup una sola
  volta per itera
esigenza: Ottimizzare cicli th:each molto lunghi che effettuano calcoli o trasformazioni
  su ogni riga.
tech: thymeleaf
tags:
- thymeleaf
- performance tuning & caching
codice: '<!-- PATTERN DA EVITARE: ogni espressione SpEL viene rivalutata per ogni
  colonna della riga. Con 1000 righe, hasRole() viene chiamato 3000 volte invece di
  1000. --> <tr th:each="user : ${users}"> <td th:text="${user.name}">Nome</td> <!--
  hasRole() rivalutato per ogni td --> <td th:class="${user.hasRole(''ADMIN'')} ?
  ''badge-danger'' : ''badge-secondary''" th:text="${user.hasRole(''ADMIN'')} ? ''Admin''
  : ''User''">Ruolo</td> <!-- formatCurrency rivalutato due volte per riga --> <td
  th:text="${#finance.formatCurrency(user.totalSpent, ''EUR'')}">€ 0</td> <td th:class="${user.totalSpent.compareTo(T(java.math.BigDecimal).valueOf(1000))
  > 0} ? ''text-gold'' : ''''" th:text="${user.totalSpent.compareTo(T(java.math.BigDecimal).valueOf(1000))
  > 0} ? ''VIP'' : ''Standard''">Tier</td> </tr> <!-- PATTERN CORRETTO: th:with calcola
  ogni valore una sola volta per iterazione. Con 1000 righe: hasRole() chiamato 1000
  volte, formatCurrency 1000 volte. --> <tr th:each="user : ${users}" th:with=" isAdmin=${user.hasRole(''ADMIN'')},
  formattedSpent=${#finance.formatCurrency(user.totalSpent, ''EUR'')}, isVip=${user.totalSpent.compareTo(T(java.math.BigDecimal).valueOf(1000))
  > 0}, rowCssClass=${user.active ? '''' : ''table-secondary''}" th:class="${rowCssClass}">
  <td th:text="${user.name}">Nome</td> <!-- Uso la variabile locale: zero reflection
  aggiuntiva --> <td th:class="${isAdmin} ? ''badge-danger'' : ''badge-secondary''"
  th:text="${isAdmin} ? ''Admin'' : ''User''">Ruolo</td> <td th:text="${formattedSpent}">€
  0</td> <td th:class="${isVip} ? ''text-gold'' : ''''" th:text="${isVip} ? ''VIP''
  : ''Standard''">Tier</td> </tr> <!-- th:with annidato per logiche più complesse:
  calcolo il subtotale e il discount una sola volta. --> <tbody th:each="order : ${orders}"
  th:with=" subtotal=${order.items.stream().mapToDouble(i -> i.price * i.quantity).sum()},
  hasDiscount=${order.coupon != null and order.coupon.active}, discountAmount=${order.coupon
  != null} ? ${subtotal * order.coupon.rate} : 0, finalTotal=${subtotal - discountAmount}">
  <tr> <td th:text="${order.id}">ID</td> <td th:text="${#finance.formatCurrency(subtotal,
  ''EUR'')}">Subtotale</td> <td th:if="${hasDiscount}" th:text="''-'' + ${#finance.formatCurrency(discountAmount,
  ''EUR'')}">Sconto</td> <td th:text="${#finance.formatCurrency(finalTotal, ''EUR'')}">Totale</td>
  </tr> </tbody> <!-- th:with può essere usato anche fuori dai loop per evitare chiamate
  ripetute a bean Spring: --> <div th:with="config=${@appConfigBean.getDisplayConfig()}">
  <span th:text="${config.maxItems}">10</span> <span th:text="${config.dateFormat}">dd/MM/yyyy</span>
  <span th:text="${config.currency}">EUR</span> </div>'
---

Problema: Degradazione delle performance dovuta a chiamate ridondanti a metodi del modello o dei bean all'interno dei loop. Perché: Uso variabili locali di template. Ho scelto th:with per "congelare" il valore calcolato, riducendo il carico sul processore SpEL e migliorando la leggibilità del codice.