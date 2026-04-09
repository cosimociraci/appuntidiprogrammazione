---
layout: post
title: "Content Security Policy (CSP) e Nonces"
date: 2026-08-17 12:00:00
sintesi: >
  Gli attacchi XSS iniettano script malevoli nel DOM. Una CSP rigorosa può bloccare l'esecuzione di script non autorizzati. I Nonces (numeri usati una sola volta) sono token casuali generati dal server a ogni richiesta, inclusi sia nell'header HTTP che
tech: "javascript"
tags: ["js", "security & cryptography"]
pdf_file: "content-security-policy-csp-e-nonces.pdf"
---

## Esigenza Reale
Proteggere un'applicazione single-page (SPA) complessa che visualizza contenuti generati dagli utenti.

## Analisi Tecnica
**Problema:** Esecuzione di script non autorizzati iniettati tramite commenti, profili utente o parametri URL malformati.
**Perché:** Implemento una politica "Nonce-based". Ho scelto questo approccio dinamico per permettere l'esecuzione di script interni legittimi bloccando al contempo qualsiasi codice iniettato esternamente.

## Esempio Implementativo

```javascript
/* Genero un nonce crittograficamente casuale per ogni richiesta HTTP. Il nonce
    deve essere diverso per ogni risposta: se fosse fisso, un attaccante
    potrebbe usarlo per bypassare la CSP. */
const crypto = require('crypto');
function generateNonce() {
    return crypto.randomBytes(16).toString('base64');
    // 128 bit di entropia
}
/* Middleware Express che genera il nonce e imposta la CSP header. */
function cspMiddleware(req, res, next) {
    const nonce = generateNonce();
    res.locals.nonce = nonce;
    // Disponibile ai template Thymeleaf/EJS/Handlebars // CSP completa:
        definisce fonti autorizzate per ogni tipo di risorsa
        res.setHeader('Content-Security-Policy', [ `default-src 'self'`, //
        Default: solo origine propria `script-src 'self' 'nonce-$
    {
        nonce
    }
    '`,
    // Script: solo src propria o con il nonce corretto `style-src 'self'
        'nonce-$
    {
        nonce
    }
    ' https:
    //fonts.googleapis.com`, // CSS: idem + Google Fonts `img-src 'self' data:
        https:`, // Immagini: src propria, data URI, HTTPS `font-src 'self'
        https://fonts.gstatic.com`, // Font: src propria + Google Fonts
        `connect-src 'self' wss://api.myapp.com`, // XHR/WebSocket: src propria
        + WS API `frame-src 'none'`, // Nessun iframe consentito `object-src
        'none'`, // Nessun plugin (Flash, etc.) `base-uri 'self'`, // Previene
        attacchi con tag <base> `form-action 'self'`, // Form solo verso origine
        propria `upgrade-insecure-requests`, // Upgrade automatico HTTP -> HTTPS
        `report-uri /api/csp-violation` // Endpoint per raccogliere le
        violazioni ].join('
    ;
    '));
    next();
}
app.use(cspMiddleware);
/* Template HTML che usa il nonce per gli script interni: */
// <script nonce="<%= nonce %>"> // // Questo script viene eseguito: ha il nonce
    corretto // initializeApp()
;
// </script> // <script> // // Questo viene BLOCCATO dalla CSP: nessun nonce //
    alert('XSS injection')
;
// </script> /* Endpoint per raccogliere le violazioni CSP e monitorarle in
    produzione: */ app.post('/api/csp-violation', express.json(
{
    type: 'application/csp-report'
}
), (req, res) => {
    const report = req.body['csp-report'];
    console.warn('CSP Violation:', {
        blockedUri: report['blocked-uri'], violatedDirective:
            report['violated-directive'], documentUri: report['document-uri'],
            ip: req.ip
    }
    );
    // Invio a sistema di alerting per rilevare attacchi XSS in corso
        alerting.track('csp_violation', report)
    ;
    res.status(204).end();
}
);
/* Implemento anche gli header di sicurezza complementari: */
function securityHeadersMiddleware(req, res, next) {
    res.setHeader('X-Content-Type-Options', 'nosniff');
    // Previene MIME sniffing res.setHeader('X-Frame-Options', 'DENY')
    ;
    // Previene clickjacking res.setHeader('X-XSS-Protection', '1
    ;
    mode=block');
    // Legacy XSS filter res.setHeader('Referrer-Policy',
        'strict-origin-when-cross-origin')
    ;
    res.setHeader('Permissions-Policy', 'camera=(), microphone=(),
        geolocation=()');
    res.setHeader('Strict-Transport-Security', 'max-age=31536000;
    includeSubDomains;
    preload');
    next();
}
```
