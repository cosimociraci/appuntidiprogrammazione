---
layout: post
title: "Security Dialect: sec:authorize"
date: 2026-04-15 12:00:00
sintesi: >
  Nascondere elementi via CSS (display:none) non è sicurezza: l'HTML è visibile nel sorgente. L'attributo sec:authorize="hasRole(...)" impedisce fisicamente al server di generare e inviare il markup al browser se l'utente non ha i permessi. Questo ridu
tech: "thymeleaf"
tags: ["thymeleaf", "security & spel expressions"]
pdf_file: "security-dialect-secauthorize.pdf"
---

## Esigenza Reale
Mostrare il pannello di controllo o i pulsanti di eliminazione solo agli utenti con privilegi amministrativi.

## Analisi Tecnica
Problema: Esposizione di informazioni riservate o strutture URL sensibili nel codice sorgente della pagina inviata a utenti comuni. Perché: Autorizzazione lato server. Ho scelto il dialetto di sicurezza per rimuovere i nodi DOM alla radice, garantendo che nessun dato sensibile lasci mai la memoria del server per utenti non autorizzati.

## Esempio Implementativo

```java
/* Aggiungo la dipendenza del Security Dialect al pom.xml: */
// <dependency> // <groupId>org.thymeleaf.extras</groupId> //
    <artifactId>thymeleaf-extras-springsecurity6</artifactId> // </dependency>
    /* Spring Boot auto-configura il dialetto se la dipendenza è nel classpath.
    Per configurazione esplicita: */ @Configuration public class
    ThymeleafSecurityConfig
{
    @Bean public SpringSecurityDialect springSecurityDialect() {
        return new SpringSecurityDialect();
    }
}
<!-- Namespace da aggiungere al tag html: --> <!-- <html xmlns:sec="http:
//www.thymeleaf.org/extras/spring-security"> --> <!-- CASO 1: Visibilità basata
    su ruolo. Il div NON viene nemmeno generato per gli utenti non-admin: il
    browser non riceve l'HTML, non solo non lo vede. --> <div
    sec:authorize="hasRole('ADMIN')"> <h3>Pannello Amministrazione</h3> <p
    th:text="$
{
    adminStats.totalUsers
}
">0</p> <a href="/admin/users">Gestisci Utenti</a> <button
    th:onclick="'deleteAll()'">Elimina tutto</button> </div> <!-- CASO 2:
    Espressioni SpEL di sicurezza complesse. --> <!-- Visibile solo a MANAGER o
    ADMIN nella stessa organizzazione dell'utente corrente --> <div
    sec:authorize="hasAnyRole('ADMIN','MANAGER') and
@securityService.isSameOrg(authentication, #orgId)"> <h4>Report
    Organizzazione</h4> </div> <!-- CASO 3: Accesso basato su permessi granulari
    (non solo ruoli). --> <button sec:authorize="hasAuthority('product:delete')"
    th:attr="data-id=${
    product.id
}
" class="btn btn-danger" onclick="deleteProduct(this.dataset.id)"> Elimina
    </button> <!-- CASO 4: Autenticazione e informazioni utente nel template.
    --> <!-- Mostro il profilo solo se autenticato --> <div
    sec:authorize="isAuthenticated()"> <span>Benvenuto, </span> <!-- Accedo ai
    dettagli dell'utente autenticato --> <span
    sec:authentication="principal.username">utente</span> <span> (</span><span
    sec:authentication="principal.authorities">ruoli</span><span>)</span> </div>
    <!-- Link di login/logout condizionale --> <a sec:authorize="isAnonymous()"
    href="/login">Accedi</a> <form sec:authorize="isAuthenticated()" th:action="
@{
    /logout
}
" method="post"> <input type="hidden" th:name="${
    _csrf.parameterName
}
" th:value="${
    _csrf.token
}
"> <button type="submit" class="btn btn-outline-secondary">Esci</button> </form>
    <!-- CASO 5: Combinare sec:authorize con th:if per logica mista. --> <tr
    th:each="user : ${
    users
}
" th:with="isOwner=${
    user.id == #authentication.principal.id
}
"> <td th:text="${
    user.name
}
">Nome</td> <!-- Il pulsante "Modifica" è visibile solo se l'utente è il
    proprietario o admin --> <td> <a th:if="${
    isOwner
}
" th:href="
@{
    '/users/' + ${
        user.id
    }
    + '/edit'
}
">Modifica</a> <button sec:authorize="hasRole('ADMIN')" th:attr="data-userid=${
    user.id
}
" class="btn btn-danger btn-sm"> Elimina (Admin) </button> </td> </tr>
/* Definisco un SecurityService per logiche di autorizzazione complesse
    richiamabili da SpEL: */
@Service("securityService") public class SecurityService {
    public boolean isSameOrg(Authentication auth, Long orgId) {
        if (!(auth.getPrincipal() instanceof UserDetails userDetails)) return
            false;
        UserEntity user =
            userRepository.findByUsername(userDetails.getUsername());
        return user != null && user.getOrganizationId().equals(orgId);
    }
    public boolean canEditProduct(Authentication auth, Long productId) {
        return hasRole(auth, "ADMIN") || productRepository.isOwner(productId,
            auth.getName());
    }
}
```
