---
layout: post
title: "Synthetic Local Variables (#ids)"
date: 2026-03-31 18:54:50 
sintesi: "In loop complessi, generare ID univoci per l'accessibilità (ARIA) o per JS è difficile. L'oggetto #ids.seq('myId') genera una sequenza incrementale che persiste per tutta la richiesta. Questo garantisce che i tag label e input siano sempre sincronizz"
tech: thymeleaf
tags: [thymeleaf, "advanced layout & templating"]
pdf_file: "synthetic-local-variables-ids.pdf"
---

## Esigenza Reale
Generare ID univoci per i campi di un form dinamico dove l'utente può aggiungere righe a piacimento.

## Analisi Tecnica
Problema: ID duplicati nel DOM che causano malfunzionamenti negli script JS e violazioni delle norme di accessibilità. Perché: Uso il generatore di sequenze di Thymeleaf. Ho scelto #ids per delegare al motore di template la gestione della numerazione progressiva dei componenti riutilizzabili.

## Esempio Implementativo

```thymeleaf
<!-- CASO BASE: checkbox con label associata tramite #ids.seq e #ids.prev. #ids.seq('chk') genera un ID con suffisso incrementale: "chk1", "chk2", "chk3"... #ids.prev('chk') riferisce l'ID generato dall'ultima chiamata a seq('chk') sullo stesso elemento. -->
<ul>
    <li th:each="permission : ${permissions}">
        <input
            type="checkbox"
            th:id="${#ids.seq('perm')}"
            th:name="permissions"
            th:value="${permission.code}"
            th:checked="${permission.assigned}"
        />
        <label th:for="${#ids.prev('perm')}" th:text="${permission.label}">Permesso</label>
    </li>
</ul>
<!-- Output generato: -->
<!-- <input type="checkbox" id="perm1" name="permissions" value="READ"> -->
<!-- <label for="perm1">Lettura</label> -->
<!-- <input type="checkbox" id="perm2" name="permissions" value="WRITE"> -->
<!-- <label for="perm2">Scrittura</label> -->
<!-- CASO AVANZATO: form dinamico con più campi per riga, ciascuno con ID univoco. Ogni riga ha un gruppo di input associati: tutti condividono il suffisso incrementale della riga. -->
<div class="form-row" th:each="item : ${orderItems}">
    <!-- #ids.seq genera il numero della riga: usato come suffisso per tutti i campi -->
    <div th:with="rowId=${#ids.seq('row')}">
        <!-- Campo prodotto -->
        <label th:for="'product-' + ${rowId}">Prodotto</label>
        <input
            type="text"
            th:id="'product-' + ${rowId}"
            th:name="'items[__${itemStat.index}__].productName'"
            th:value="${item.productName}"
            class="form-control"
        />
        <!-- Campo quantità: ID correlato alla stessa riga -->
        <label th:for="'qty-' + ${rowId}">Quantità</label>
        <input
            type="number"
            th:id="'qty-' + ${rowId}"
            th:name="'items[__${itemStat.index}__].quantity'"
            th:value="${item.quantity}"
            class="form-control"
            min="1"
        />
        <!-- Campo prezzo: stessa riga -->
        <label th:for="'price-' + ${rowId}">Prezzo</label>
        <input
            type="number"
            th:id="'price-' + ${rowId}"
            th:name="'items[__${itemStat.index}__].price'"
            th:value="${item.price}"
            class="form-control"
            step="0.01"
        />
    </div>
</div>
<!-- CASO COMPONENTI RIUTILIZZABILI: un frammento che usa #ids funziona correttamente anche se incluso più volte nella stessa pagina. Ogni inclusione genera ID distinti. -->
<div th:fragment="toggle-panel(title, content)">
    <div th:with="panelId=${#ids.seq('panel')}">
        <button
            class="btn btn-outline-secondary"
            th:attr="data-bs-toggle='collapse', data-bs-target='#collapse-' + ${panelId}"
            th:text="${title}"
        >
            Titolo
        </button>
        <div th:id="'collapse-' + ${panelId}" class="collapse">
            <p th:text="${content}">Contenuto</p>
        </div>
    </div>
</div>
<!-- Due inclusioni dello stesso frammento: ID distinti garantiti -->
<th:block th:replace="~{:: toggle-panel('Sezione A', 'Contenuto A')}"></th:block>
<th:block th:replace="~{:: toggle-panel('Sezione B', 'Contenuto B')}"></th:block>
<!-- Genera: collapse-1 e collapse-2, mai duplicati -->

```
