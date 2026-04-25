---
layout: code
title: "Invokedynamic e Lambda Metafactory"
date: 2027-07-07 12:00:00
sintesi: >
  Le Lambda in Java non sono semplici classi anonime, ma usano l'istruzione invokedynamic. La LambdaMetafactory permette di generare "al volo" un'implementazione di un'interfaccia funzionale collegandola a un metodo esistente. Questo evita la creazione
tech: "java"
tags: ["java"]
pdf_file: "invokedynamic-e-lambda-metafactory.pdf"
---

## Esigenza Reale
Trasformare stringhe di configurazione o espressioni dinamiche in chiamate a funzioni Java reali e veloci.

## Analisi Tecnica
**Problema:** L'uso eccessivo di classi anonime per le callback appesantisce il caricamento delle classi e il consumo di memoria.

**Perché:** Sfrutto LambdaMetafactory. Ho scelto questa tecnica per generare invocatori dinamici che la JVM tratta come normali lambda, garantendo il massimo livello di inlining possibile.

## Esempio Implementativo

```java
/* Trasformo un MethodHandle in una Function<String, String> tramite
    LambdaMetafactory. Il risultato è un'implementazione dell'interfaccia
    funzionale generata a runtime e ottimizzata dalla JVM come una lambda
    normale. */
public class DynamicFunctionFactory {
    public static Function<String, String> createFunction(Class<?> targetClass,
        String methodName) throws Throwable {
        MethodHandles.Lookup lookup = MethodHandles.lookup();
        // Trovo il metodo target MethodHandle targetHandle =
            lookup.findVirtual( targetClass, methodName,
            MethodType.methodType(String.class, String.class))
        ;
        // Genero un'implementazione di Function<String,String> che delega al
            metodo target CallSite callSite = LambdaMetafactory.metafactory(
            lookup, "apply", // Il metodo dell'interfaccia funzionale da
            implementare MethodType.methodType(Function.class, targetClass), //
            Tipo del factory MethodType.methodType(Object.class, Object.class),
            // Firma erased della SAM targetHandle, // Il metodo reale da
            invocare MethodType.methodType(String.class, String.class) // Firma
            specializzata )
        ;
        // Ottengo il factory e lo invoco con l'istanza target
            @SuppressWarnings("unchecked") Function<String, String> fn =
            (Function<String, String>) callSite.getTarget().invoke(targetClass.g
            etDeclaredConstructor().newInstance())
        ;
        return fn;
    }
}
/* Implemento un motore di regole basato su LambdaMetafactory per una pipeline
    di trasformazione: */
@Component public class RuleEngine {
    // Mappa nome-regola -> Function generata via LambdaMetafactory private
        final Map<String, Function<String, String>> rules = new
        ConcurrentHashMap<>()
    ;
    @PostConstruct public void loadRules() throws Throwable {
        // Carico le regole da configurazione e genero le Function dinamicamente
            for (RuleConfig config : ruleConfigRepository.findAll())
        {
            Function<String, String> fn = DynamicFunctionFactory.createFunction(
                Class.forName(config.getClassName()), config.getMethodName() );
            rules.put(config.getRuleName(), fn);
            log.info("Regola '{
            }
            ' caricata come lambda dinamica", config.getRuleName());
        }
    }
    public String applyRule(String ruleName, String input) {
        Function<String, String> rule = rules.get(ruleName);
        if (rule == null) throw new IllegalArgumentException("Regola non
            trovata: " + ruleName);
        return rule.apply(input);
        // Il JIT ottimizza questa chiamata come una lambda normale
    }
}
/* Confronto con la reflection classica per quantificare il guadagno: */
@Benchmark public String withReflection(BenchState state) throws Exception {
    return (String) state.method.invoke(state.instance, state.input);
    // Overhead ad ogni chiamata
}
@Benchmark public String withLambdaMetafactory(BenchState state) {
    return state.dynamicFunction.apply(state.input);
    // Ottimizzato dal JIT come lambda normale
}
// LambdaMetafactory è tipicamente 5-20x più veloce della reflection su call
    site caldi /* In Spring Boot, uso questo pattern per un sistema di
    validazione configurabile: */ @Service public class DynamicValidatorService
{
    private final Map<String, Predicate<String>> validators = new
        ConcurrentHashMap<>();
    public void registerValidator(String name, Class<?> cls, String methodName)
        throws Throwable {
        // Genero un Predicate<String> dinamico che delega al metodo del
            validatore validators.put(name, createPredicate(cls, methodName))
        ;
    }
    public boolean validate(String validatorName, String value) {
        return validators.getOrDefault(validatorName, s -> true).test(value);
    }
}
```
