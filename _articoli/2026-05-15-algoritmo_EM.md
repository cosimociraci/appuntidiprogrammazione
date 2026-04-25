---
layout: code
title: "L'algoritmo EM (Expectation-Maximization)"
sintesi: >
  L'algoritmo EM (Expectation-Maximization) è un metodo iterativo fondamentale in statistica e machine learning, utilizzato per trovare stime di massima verosimiglianza dei parametri in modelli probabilistici che dipendono da variabili latenti.
date: 2026-05-15 12:00:00
tech: "ia"
tags: ["ia"]
link: ""
---
# L’Algoritmo EM (Expectation–Maximization)  
L’algoritmo **EM (Expectation–Maximization)** è uno dei pilastri della statistica computazionale e del machine learning.  
La sua forza sta nella capacità di stimare parametri anche quando i dati sono **incompleti**, **rumorosi** o quando esistono **variabili latenti** (cioè non osservabili direttamente).

In altre parole: EM è l’algoritmo che usi quando “ti manca un pezzo del puzzle”, ma vuoi comunque ricostruire l’immagine completa.

---

## Perché serve l’EM?

Molti modelli probabilistici dipendono da fattori nascosti.  
Esempi tipici:

- cluster non osservati (come nei **Gaussian Mixture Models**)  
- categorie mancanti  
- dati incompleti o parziali  
- modelli generativi con variabili latenti  

In questi casi, massimizzare direttamente la verosimiglianza  


\[
L(\theta) = \ln P(X|\theta)
\]

  
è difficile perché dipende da variabili non osservate \(Z\).  
L’algoritmo EM risolve il problema iterando due fasi complementari.

---

# Come funziona: i due step fondamentali

## E-Step — *Expectation*  
In questa fase stimiamo i valori attesi delle variabili latenti.

**Cosa fa:**  
Calcola la probabilità che ogni dato osservato appartenga a una certa componente del modello, usando i parametri correnti.

**Esempio intuitivo:**  
Se stiamo raggruppando punti in cluster, l’E-Step calcola la probabilità che ogni punto appartenga a ciascun cluster.

---

## M-Step — *Maximization*  
Qui aggiorniamo i parametri del modello.

**Cosa fa:**  
Ricalcola i parametri (es. media, varianza, pesi) massimizzando la verosimiglianza, usando le probabilità calcolate nell’E-Step.

**Esempio intuitivo:**  
I centri dei cluster vengono spostati per adattarsi meglio ai punti che “probabilmente” appartengono a quel cluster.

---

# Applicazioni classiche

## Gaussian Mixture Model (GMM)

Immagina di osservare solo l’altezza di una popolazione mista uomini/donne, ma senza sapere chi appartiene a quale gruppo.

- **E-Step:** stimi la probabilità che ogni persona sia uomo o donna.  
- **M-Step:** aggiorni media e varianza delle due gaussiane.

Il processo si ripete finché i parametri non convergono.

---

## Clustering: K-Means come caso particolare

Il K-Means può essere visto come una versione “rigida” dell’EM:

- K-Means → ogni punto appartiene a un solo cluster (**hard assignment**)  
- EM → ogni punto ha una probabilità di appartenere a ciascun cluster (**soft assignment**)  

Questo rende EM più flessibile e più adatto a dati complessi.

---

# Punti di forza e criticità

### ✅ Vantaggi
- La verosimiglianza **aumenta sempre** a ogni iterazione.  
- Gestisce in modo naturale **dati mancanti**.  
- È matematicamente elegante e ben fondato.

### Svantaggi
- Può convergere a **minimi locali** (dipende dall’inizializzazione).  
- Può essere **lento** su dataset molto grandi.

---

# Formalizzazione matematica

L’obiettivo è massimizzare:



\[
L(\theta) = \ln P(X|\theta)
\]



Poiché la presenza delle variabili latenti \(Z\) rende difficile il calcolo diretto, EM massimizza iterativamente una **lower bound** della verosimiglianza, migliorandola a ogni ciclo E/M.

---

# Esempio in Java: EM per un semplice Gaussian Mixture Model

L’esempio seguente mostra una versione **semplificata** di EM per un GMM bidimensionale (due gaussiane).  
Non è ottimizzato, ma illustra chiaramente i passaggi E-Step e M-Step.

```java
import java.util.Random;

public class SimpleGMM {

    // Numero di componenti
    private static final int K = 2;

    public static void main(String[] args) {

        double[] data = {1.0, 1.2, 0.8, 5.0, 5.2, 4.8};

        // Parametri iniziali
        double[] means = {1.0, 5.0};
        double[] variances = {1.0, 1.0};
        double[] weights = {0.5, 0.5};

        double[][] responsibilities = new double[data.length][K];

        for (int iter = 0; iter < 20; iter++) {

            // --- E-STEP ---
            for (int i = 0; i < data.length; i++) {
                double total = 0.0;

                for (int k = 0; k < K; k++) {
                    responsibilities[i][k] = weights[k] *
                            gaussian(data[i], means[k], variances[k]);
                    total += responsibilities[i][k];
                }

                // Normalizzazione
                for (int k = 0; k < K; k++) {
                    responsibilities[i][k] /= total;
                }
            }

            // --- M-STEP ---
            for (int k = 0; k < K; k++) {
                double weightSum = 0.0;
                double meanSum = 0.0;
                double varSum = 0.0;

                for (int i = 0; i < data.length; i++) {
                    weightSum += responsibilities[i][k];
                    meanSum += responsibilities[i][k] * data[i];
                }

                means[k] = meanSum / weightSum;

                for (int i = 0; i < data.length; i++) {
                    varSum += responsibilities[i][k] *
                            Math.pow(data[i] - means[k], 2);
                }

                variances[k] = varSum / weightSum;
                weights[k] = weightSum / data.length;
            }
        }

        System.out.println("Final means:");
        for (double m : means) System.out.println(m);
    }

    private static double gaussian(double x, double mean, double var) {
        return (1.0 / Math.sqrt(2 * Math.PI * var)) *
                Math.exp(-Math.pow(x - mean, 2) / (2 * var));
    }
}
```
