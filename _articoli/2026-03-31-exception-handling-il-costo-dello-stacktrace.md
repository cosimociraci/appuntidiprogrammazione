---
layout: post
title: 'Exception Handling: il costo dello Stacktrace'
date: '2026-03-31 16:25:01 '
sintesi: 'Creare un''eccezione è costoso non per l''oggetto in sé, ma per il metodo
  fillInStackTrace(), che deve percorrere l''intero call stack nativo. Per errori
  di business frequenti (es. UserNotFound), non dovremmo usare eccezioni con stacktrace.
  Una tecnica '
esigenza: Gestire validazioni di input ad alta frequenza dove il fallimento è un evento
  previsto e comune, non un errore di sistema.
tech: java
tags:
- java
- memory & performance
codice: '/* Confronto il costo di creazione di un''eccezione standard vs una ottimizzata
  con JMH: */ @Benchmark public void standardException() { try { throw new RuntimeException("Not
  found"); // fillInStackTrace() percorre 20+ frame } catch (RuntimeException e) {
  /* ignorata */ } } @Benchmark public void lightweightException() { try { throw BusinessException.NOT_FOUND;
  // Zero allocazione, zero stack walk } catch (BusinessException e) { /* ignorata
  */ } } /* Implemento la gerarchia di eccezioni di business leggere. Il costruttore
  con writableStackTrace=false bypassa completamente fillInStackTrace(). */ public
  class BusinessException extends RuntimeException { // Istanze statiche pre-allocate
  per gli errori più comuni: zero allocazione a runtime public static final BusinessException
  NOT_FOUND = new BusinessException("Risorsa non trovata"); public static final BusinessException
  UNAUTHORIZED = new BusinessException("Accesso non autorizzato"); public static final
  BusinessException VALIDATION_FAILED = new BusinessException("Validazione fallita");
  private BusinessException(String message) { // enableSuppression=false: non alloco
  la lista delle cause soppresse // writableStackTrace=false: non chiamo fillInStackTrace()
  super(message, null, false, false); } /* Per errori che richiedono un messaggio
  dinamico mantengo lo stesso pattern ma senza istanza statica: */ public static BusinessException
  of(String message) { return new BusinessException(message); } } /* In Spring Boot,
  uso le eccezioni leggere nel layer di validazione che viene invocato ad ogni richiesta:
  */ @Service public class OrderValidationService { public void validate(OrderRequest
  request) { if (request.getItems() == null || request.getItems().isEmpty()) { throw
  BusinessException.VALIDATION_FAILED; // Zero costo di creazione } if (request.getTotalAmount().compareTo(BigDecimal.ZERO)
  <= 0) { throw BusinessException.of("Importo non valido: " + request.getTotalAmount());
  } if (!productRepository.existsById(request.getProductId())) { throw BusinessException.NOT_FOUND;
  // Istanza statica: nessuna allocazione } } } /* Gestisco le BusinessException nel
  GlobalExceptionHandler senza loggare lo stacktrace (è vuoto per design): */ @RestControllerAdvice
  public class GlobalExceptionHandler { @ExceptionHandler(BusinessException.class)
  public ResponseEntity<ErrorResponse> handleBusiness(BusinessException ex) { // Non
  loggo lo stack trace: è vuoto per design e non aggiunge informazioni log.debug("Business
  rule violation: {}", ex.getMessage()); return ResponseEntity.badRequest().body(new
  ErrorResponse(ex.getMessage())); } } /* Misuro il guadagno con JMH: su 1 milione
  di lanci, le BusinessException sono 50-100x più veloci delle RuntimeException standard.
  */'
---

Problema: Overhead della CPU enorme quando le eccezioni vengono usate per gestire la logica di business ordinaria. Perché: Disabilito lo stacktrace. Ho deciso di ottimizzare le eccezioni ricorrenti perché in questi casi il "dove" è successo l'errore è già noto e non giustifica il costo del dump dello stack.