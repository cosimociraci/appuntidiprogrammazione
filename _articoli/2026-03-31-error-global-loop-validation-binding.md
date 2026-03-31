---
layout: post
title: "Error Global Loop & Validation Binding"
date: 2026-03-31 19:00:36 
sintesi: "L'oggetto #fields di Thymeleaf permette di catturare errori che non appartengono a un campo specifico (es. Credenziali non valide o Password non corrispondenti) tramite th:each=err : ${#fields.errors('global')}. L'attributo th:errorclass applica clas"
tech: thymeleaf
tags: [thymeleaf, "spring integration & flow archi"]
pdf_file: "error-global-loop-validation-binding.pdf"
---

## Esigenza Reale
Gestire la validazione di form complessi con regole cross-field (es. la data di fine deve essere dopo la data di inizio).

## Analisi Tecnica
Problema: Codice di template sporco e ripetitivo per gestire la visualizzazione degli errori di validazione del backend. Perché: Uso l'astrazione #fields. Ho scelto di centralizzare la logica di visualizzazione degli errori per garantire che ogni feedback del server sia mappato correttamente agli elementi UI corrispondenti nel DOM.

## Esempio Implementativo

```thymeleaf
/* Definisco validatori cross-field tramite annotazione custom a livello di classe. */
@Target(ElementType.TYPE) @Retention(RetentionPolicy.RUNTIME) @Constraint(validatedBy =
DateRangeValidator.class) public @interface ValidDateRange { String message() default "La data di
fine deve essere successiva alla data di inizio"; Class<?>[] groups() default {}; Class<? extends
Payload>[] payload() default {}; } public class DateRangeValidator implements
ConstraintValidator<ValidDateRange, EventFormDto>
    { @Override public boolean isValid(EventFormDto form, ConstraintValidatorContext ctx) { if
    (form.getStartDate() == null || form.getEndDate() == null) return true; if
    (form.getEndDate().isBefore(form.getStartDate())) { // Aggiungo l'errore come global (non legato
    a un campo): ctx.disableDefaultConstraintViolation(); ctx.buildConstraintViolationWithTemplate(
    "La data di fine (" + form.getEndDate() + ") deve essere dopo la data di inizio (" +
    form.getStartDate() + ")") .addConstraintViolation(); return false; } return true; } } /* DTO
    con validazioni a livello di campo e cross-field. */ @ValidDateRange // Validazione cross-field:
    errore "global" public class EventFormDto { @NotBlank(message = "Il titolo è obbligatorio")
    @Size(min = 3, max = 100, message = "Il titolo deve avere tra 3 e 100 caratteri") private String
    title; @NotNull(message = "La data di inizio è obbligatoria") @FutureOrPresent(message = "La
    data di inizio non può essere nel passato") @DateTimeFormat(pattern = "yyyy-MM-dd") private
    LocalDate startDate; @NotNull(message = "La data di fine è obbligatoria")
    @DateTimeFormat(pattern = "yyyy-MM-dd") private LocalDate endDate; @Min(value = 1, message = "La
    capienza minima è 1 partecipante") @Max(value = 10000, message = "La capienza massima è 10.000
    partecipanti") private Integer capacity; @Email(message = "L'email del contatto non è valida")
    private String contactEmail; } /* Controller che gestisce gli errori di binding e validazione.
    */ @PostMapping("/events") public String createEvent(@ModelAttribute @Valid EventFormDto form,
    BindingResult result, Model model) { if (result.hasErrors()) { // Non devo aggiungere form al
    model: Spring lo mantiene automaticamente come "eventFormDto" return "events/new"; // Torno al
    form con gli errori popolati } eventService.create(form); return "redirect:/events"; }
    <!-- Template events/new.html: gestione completa degli errori con #fields. -->
    <form th:object="${eventFormDto}" th:action="@{/events}" method="post">
        <!-- ERRORI GLOBALI (cross-field): non associati a un campo specifico -->
        <div th:if="${#fields.hasGlobalErrors()}" class="alert alert-danger" role="alert">
            <strong>Errori di validazione:</strong>
            <ul class="mb-0">
                <li th:each="err : ${#fields.globalErrors()}" th:text="${err}">Errore globale</li>
            </ul>
        </div>
        <!-- Alternativa: mostro TUTTI gli errori in cima (globali + di campo) -->
        <div th:if="${#fields.hasAnyErrors()}" class="alert alert-warning d-none d-print-block">
            <!-- Utile per la stampa o per screen reader -->
            <ul>
                <li th:each="err : ${#fields.allErrors()}" th:text="${err}">Errore</li>
            </ul>
        </div>
        <!-- CAMPO TITOLO: th:errorclass aggiunge 'is-invalid' se il campo ha errori -->
        <div class="mb-3">
            <label for="title" class="form-label">Titolo *</label>
            <!-- th:errorclass: aggiunge la classe CSS solo se #fields.hasErrors('title') è true -->
            <input
                type="text"
                th:field="*{title}"
                th:errorclass="is-invalid"
                class="form-control"
                id="title"
            />
            <!-- Mostra il primo messaggio di errore per questo campo -->
            <div th:if="${#fields.hasErrors('title')}" class="invalid-feedback">
                <span th:errors="*{title}">Errore titolo</span>
            </div>
        </div>
        <!-- CAMPO DATA INIZIO: con indicatore visivo dello stato -->
        <div class="mb-3">
            <label for="startDate" class="form-label">Data inizio *</label>
            <input
                type="date"
                th:field="*{startDate}"
                th:errorclass="is-invalid"
                th:classappend="${#fields.hasErrors('startDate')} ? '' : (${eventFormDto.startDate} != null ? 'is-valid' : '')"
                class="form-control"
                id="startDate"
            />
            <div th:if="${#fields.hasErrors('startDate')}" class="invalid-feedback">
                <span th:errors="*{startDate}">Errore data</span>
            </div>
        </div>
        <!-- CAMPO CAPIENZA: errori multipli su stesso campo -->
        <div class="mb-3">
            <label for="capacity" class="form-label">Capienza massima *</label>
            <input
                type="number"
                th:field="*{capacity}"
                th:errorclass="is-invalid"
                class="form-control"
                id="capacity"
                min="1"
                max="10000"
            />
            <!-- Se ci sono più errori sullo stesso campo, li mostro tutti -->
            <div th:if="${#fields.hasErrors('capacity')}" class="invalid-feedback">
                <ul class="mb-0 ps-3">
                    <li th:each="err : ${#fields.errors('capacity')}" th:text="${err}">Errore</li>
                </ul>
            </div>
        </div>
        <button type="submit" class="btn btn-primary">Crea Evento</button>
    </form></ValidDateRange,
>

```
