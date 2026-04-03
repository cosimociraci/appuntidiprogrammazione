---
layout: post
title: "Dynamic Proxy e Interface Invocation"
date: 2026-04-03 14:39:43
sintesi: "I proxy dinamici sono il cuore di @Mapper in MyBatis o FeignClient. Quando si chiama un metodo su un'interfaccia magica, si sta invocando un InvocationHandler. Ogni chiamata passa per un array di Object[] per gli argomenti, con relativo boxing. Per o"
tech: "java"
tags: ["java", "advanced reflection & metaprogr"]
pdf_file: "dynamic-proxy-e-interface-invocation.pdf"
---

## Esigenza Reale
Creare un client HTTP dichiarativo dove basta definire l'interfaccia per avere l'implementazione automatica.

## Analisi Tecnica
Problema: Overhead introdotto dal layer di intercettazione dei proxy dinamici nelle interfacce dei repository o dei client. Perché: Implemento una cache dei Method all'interno dell'InvocationHandler. Ho scelto di pre-risolvere i riferimenti ai metodi per minimizzare il tempo speso nella gestione dei metadati durante la chiamata.

## Esempio Implementativo

```java
* Implemento un InvocationHandler ottimizzato con cache dei MethodHandler pre-
* risolti allo startup. */
 public class HttpClientInvocationHandler implements InvocationHandler 
{ 
// Pre-risolvo tutti i metodi dell'interfaccia all'atto di creazione del proxy
// private final Map<Method, MethodExecutor> methodCache = new HashMap<>();
// private final String baseUrl; private final HttpClient httpClient; public
// HttpClientInvocationHandler(Class<?> apiInterface, String baseUrl)
{ this.baseUrl = baseUrl; this.httpClient = HttpClient.newHttpClient(); 
// Pre-risolvo tutti i metodi dell'interfaccia allo startup, non a ogni chiamata
// for (Method method : apiInterface.getDeclaredMethods())
{ HttpGet annotation = method.getAnnotation(HttpGet.class); if (annotation !=
null)
{ String url = baseUrl + annotation.path(); Type returnType =
method.getGenericReturnType();
// Creo l'executor specifico per questo metodo: chiuso sulla URL e il tipo di
// ritorno methodCache.put(method, args -> executeGet(url, args, returnType)); }
 HttpPost postAnnotation = method.getAnnotation(HttpPost.class); if
(postAnnotation != null)
{ String url = baseUrl + postAnnotation.path(); methodCache.put(method, args ->
executePost(url, args)); }
 }
 }
 @Override public Object invoke(Object proxy, Method method, Object[] args)
throws Throwable
{ 
// Lookup O(1) nella cache: nessuna reflection a runtime if (method.isDefault())
{ 
// Gestisco i metodi default dell'interfaccia senza passare per la cache return
// InvocationHandler.invokeDefault(proxy, method, args); }
 MethodExecutor executor = methodCache.get(method); if (executor == null) 
{ throw new UnsupportedOperationException("Metodo non mappato: " +
method.getName()); }
 return executor.execute(args); }
 @FunctionalInterface interface MethodExecutor 
{ Object execute(Object[] args) throws Exception; }
 
/* Factory method per creare il proxy in modo type-safe: */
 @SuppressWarnings("unchecked") public static <T> T createProxy(Class<T>
apiInterface, String baseUrl)
{ return (T) Proxy.newProxyInstance( apiInterface.getClassLoader(), new Class[]
{apiInterface}
, new HttpClientInvocationHandler(apiInterface, baseUrl) ); }
 }
 
/* In Spring Boot, registro il proxy come Bean e lo inietto nei Service: */
 @Configuration public class ApiClientConfig 
{ @Bean public OrderApiClient orderApiClient(@Value("$
{api.orders.base-url}
") String baseUrl) 
{ return HttpClientInvocationHandler.createProxy(OrderApiClient.class, baseUrl);
}
 @Bean public UserApiClient userApiClient(@Value("$
{api.users.base-url}
") String baseUrl) 
{ return HttpClientInvocationHandler.createProxy(UserApiClient.class, baseUrl);
}
 }
 
/* Definisco l'interfaccia dichiarativa del client: */
 public interface OrderApiClient 
{ @HttpGet(path = "/orders/
{id}
") Order getOrder(@PathParam("id") long id); @HttpPost(path = "/orders") Order
createOrder(OrderRequest request); @HttpGet(path = "/orders") List<Order>
listOrders(@QueryParam("status") String status); }
```
