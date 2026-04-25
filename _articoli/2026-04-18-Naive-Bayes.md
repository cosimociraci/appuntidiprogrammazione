---
layout: post
title: "Naive Bayes"
date: 2026-04-18 07:25:10
sintesi: >
    In ambito tecnico, il Naive Bayes è un classificatore probabilistico basato sul Teorema di Bayes. Viene definito "Naive" (ingenuo) perché assume che la presenza di una particolare caratteristica in una classe sia totalmente slegata dalla presenza di altre.
tech: "Statistica"
tags: ["statistica"]
---

## Naive Bayes: Il Classificatore ad Alta Velocità

In ambito tecnico, il Naive Bayes è un **classificatore probabilistico basato sul Teorema di Bayes**. Viene definito "Naive" (ingenuo) perché assume che la presenza di una particolare caratteristica in una classe sia totalmente slegata dalla presenza di altre. 

Nel mondo reale, lo usiamo per:
1.  **Filtri Anti-Spam:** Analisi del testo per bloccare email pericolose.
2.  **Sentiment Analysis:** Capire se una recensione su Amazon o un tweet è positivo o negativo.
3.  **Riconoscimento Lingua:** Capire istantaneamente se un testo è scritto in inglese, italiano o codice Java.

### Sentiment Analysis (Analizzatore di Recensioni)

Immaginiamo di voler istruire un server per capire se i commenti degli utenti su un nuovo videogame sono "Entusiasti" o "Delusi".



```java
import java.util.Map;

public class SentimentAnalyzer {
    public static void main(String[] args) {
        // --- PROBABILITÀ A PRIORI (P(H)) ---
        // Basandoci su milioni di recensioni, sappiamo che 
        // mediamente il 70% degli utenti è soddisfatto.
        double probPositive = 0.7;
        double probNegative = 0.3;

        // --- MODELLO DI PROBABILITÀ CONDIZIONALE (P(E|H)) ---
        // Quanto è probabile trovare queste parole in una recensione positiva?
        Map<String, Double> positiveModel = Map.of(
            "capolavoro", 0.12, 
            "bug", 0.01,         // Molto raro in recensioni positive
            "grafica", 0.08
        );

        // Quanto è probabile trovarle in una negativa?
        Map<String, Double> negativeModel = Map.of(
            "capolavoro", 0.001, 
            "bug", 0.15,         // Molto frequente in recensioni negative
            "grafica", 0.04
        );

        // --- DATI IN INPUT (L'evidenza) ---
        String[] review = {"grafica", "bug"};

        // Calcolo della probabilità a posteriori (semplificata)
        double scorePositive = probPositive;
        double scoreNegative = probNegative;

        for (String word : review) {
            // Applichiamo la produttoria delle probabilità
            // Se la parola non esiste nel database, usiamo un valore minimo (Smoothing)
            scorePositive *= positiveModel.getOrDefault(word, 0.0001);
            scoreNegative *= negativeModel.getOrDefault(word, 0.0001);
        }

        // --- OUTPUT DEL SISTEMA ---
        System.out.println("Risultato analisi: " + 
            (scorePositive > scoreNegative ? "POSITIVE" : "NEGATIVE"));
    }
}
```

## Analisi dei Parametri Tecnici
Per dominare l'algoritmo, dobbiamo capire come reagisce alle variazioni dei suoi componenti matematici.

### 1. Probabilità a Priori ($P(C)$)
Rappresenta la conoscenza pregressa del sistema. 
* **Se aumenta:** Il modello sviluppa un *bias* (pregiudizio). Se impostiamo la probabilità di "Spam" al 99%, l'algoritmo etichetterà quasi tutto come spam, ignorando il contenuto del messaggio a meno che non ci siano prove schiaccianti del contrario.
* **Se diminuisce:** Il modello diventa scettico verso quella categoria e richiederà indizi estremamente forti per assegnarla.

### 2. Verosimiglianza o Likelihood ($P(x_i|C)$)
È la "forza" del segnale di una singola parola (o caratteristica).
* **Se aumenta:** Quella caratteristica diventa un identificatore univoco. Ad esempio, se la probabilità della parola "eseguibile.exe" è altissima nella classe "Virus", basterà trovarla una volta per far pendere l'ago della bilancia.
* **Se diminuisce:** La caratteristica diventa "rumore". Se una parola appare con la stessa probabilità sia in testi positivi che negativi, il suo peso nel calcolo finale diventa nullo.

### 3. Valore di Smoothing (Laplace Smoothing)
Nel codice è il valore `0.0001` usato quando una parola è sconosciuta.
* **Cosa accade se diminuisce troppo?** Se incontriamo una parola nuova e il valore è `0`, l'intera probabilità della frase diventa `0` (perché in matematica ogni numero moltiplicato per zero fa zero). Questo è un errore grave chiamato **Zero-Frequency Problem**.
* **Cosa accade se aumenta?** Se il valore di default è troppo alto, le parole nuove "annegano" l'importanza di quelle conosciute, rendendo l'algoritmo impreciso e incerto.

### 4. Numero di Caratteristiche (Input Array)
* **All'aumentare dei dati:** Il Naive Bayes brilla. Più indizi (parole) inseriamo, più il calcolo diventa preciso, poiché le piccole incertezze si compensano a vicenda. È uno dei pochi algoritmi che non rallenta drasticamente con l'aumentare dei dati.
