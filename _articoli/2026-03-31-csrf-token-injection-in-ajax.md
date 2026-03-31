---
layout: post
title: "CSRF Token Injection in AJAX"
date: 2026-03-31 18:54:51 
sintesi: "I form standard di Thymeleaf gestiscono i token CSRF automaticamente, ma le chiamate AJAX/VanillaJS no. Le espressioni ${_csrf.parameterName} e ${_csrf.token} permettono di iniettare i valori nei tag meta. Questo permette agli script lato client di l"
tech: thymeleaf
tags: [thymeleaf, "security & spel expressions"]
pdf_file: "csrf-token-injection-in-ajax.pdf"
---

## Esigenza Reale
Proteggere le chiamate asincrone effettuate via fetch() o XMLHttpRequest contro attacchi di falsificazione della richiesta.

## Analisi Tecnica
Problema: Le richieste asincrone falliscono con errore 403 perché non includono il segreto crittografico richiesto da Spring Security. Perché: Esposizione sicura del token. Ho scelto di usare i meta-tag per centralizzare il segreto CSRF, rendendolo accessibile in modo trasparente a tutti i moduli JavaScript della pagina.

## Esempio Implementativo

```thymeleaf
<!-- Inserisco i meta-tag CSRF nel layout base: disponibili in tutte le pagine. Thymeleaf inietta i valori correnti del token generato da Spring Security per questa sessione. -->
<head>
    <meta name="_csrf" th:content="${_csrf.token}" />
    <meta name="_csrf_header" th:content="${_csrf.headerName}" />
    <!-- Oppure uso th:attr per sicurezza se il nome dell'attributo è dinamico: -->
    <meta th:attr="name=${_csrf.parameterName},content=${_csrf.token}" />
</head>
/* Modulo JavaScript centralizzato (csrf.js): leggo i meta-tag una sola volta e li rendo disponibili
a tutti i moduli fetch della pagina. */ const CsrfUtils = (() => { // Leggo i valori dal DOM una
sola volta al caricamento della pagina const tokenElement =
document.querySelector('meta[name="_csrf"]'); const headerElement =
document.querySelector('meta[name="_csrf_header"]'); if (!tokenElement || !headerElement) {
console.error('Meta-tag CSRF non trovati: le richieste POST falliranno con 403.'); } const token =
tokenElement?.content; const headerName = headerElement?.content; /* Wrapper fetch con CSRF
automatico: sostituzione drop-in di window.fetch per tutte le richieste mutanti. */ function
secureFetch(url, options = {}) { const method = (options.method || 'GET').toUpperCase(); // GET e
HEAD non necessitano di CSRF (idempotenti per design) if (['GET', 'HEAD',
'OPTIONS'].includes(method)) { return fetch(url, options); } // Aggiungo il token CSRF a tutte le
richieste mutanti const headers = new Headers(options.headers || {}); headers.set(headerName,
token); return fetch(url, { ...options, headers }); } /* Funzione helper per form AJAX: serializza
il FormData e aggiunge il CSRF. */ function submitForm(form) { const formData = new FormData(form);
// Spring Security accetta il token anche come parametro di form
formData.append(document.querySelector('meta[name="_csrf"]')?.getAttribute('name') || '_csrf',
token); return fetch(form.action, { method: form.method || 'POST', body: formData // NON imposto
Content-Type: il browser lo fa automaticamente con il boundary multipart }); } return { token,
headerName, secureFetch, submitForm }; })(); /* Esempio d'uso: */ async function
deleteProduct(productId) { const response = await
CsrfUtils.secureFetch(`/api/products/${productId}`, { method: 'DELETE' }); if (response.ok) {
document.getElementById(`product-${productId}`).remove(); } else if (response.status === 403) {
console.error('CSRF token non valido o scaduto: ricarica la pagina.'); } } /* Per HTMX, configuro il
token CSRF globalmente: */ document.addEventListener('htmx:configRequest', (event) => { // HTMX
legge i meta-tag automaticamente se configurato correttamente
event.detail.headers[CsrfUtils.headerName] = CsrfUtils.token; }); /* Configurazione Spring Security
per accettare il token sia come header che come parametro: */ @Configuration public class
SecurityConfig { @Bean public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
http .csrf(csrf -> csrf .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse()) //
Permette la lettura del token via JS per SPA .csrfTokenRequestHandler(new
CsrfTokenRequestAttributeHandler()) ) // ... resto della configurazione return http.build(); } }

```
