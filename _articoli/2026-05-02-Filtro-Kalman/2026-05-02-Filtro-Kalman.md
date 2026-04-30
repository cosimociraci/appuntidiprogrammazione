---
layout: post
title: "Filtro di Kalman"
sintesi: >
Il Filtro di Kalman è un algoritmo matematico ricorsivo che permette di stimare lo stato di un sistema dinamico partendo da misure incerte e disturbate da "rumore". È il cervello dietro ai sistemi di navigazione dei droni, alla guida autonoma delle auto e al tracciamento dei razzi spaziali.
date: 2026-05-02 07:27:10
tech: "Statistica"
tags: [Statistica, Classificazione, Filtro di Kalman, Ranking, LLM]
---
Il **Filtro di Kalman** è un algoritmo matematico ricorsivo che permette di stimare lo stato di un sistema dinamico partendo da misure incerte e disturbate da "rumore". È il cervello dietro ai sistemi di navigazione dei droni, alla guida autonoma delle auto e al tracciamento dei razzi spaziali.

A differenza di una semplice media, il Filtro di Kalman è intelligente: decide quanto fidarsi dei propri calcoli e quanto fidarsi dei sensori, cambiando strategia istante per istante.

---

### Telemetria di un Drone in Volo

Immaginiamo un drone che deve mantenere una posizione stabile. Il GPS ha un errore di qualche metro (rumore di misura) e il vento sposta il drone in modo imprevedibile (rumore di processo). Il Filtro di Kalman fonde i dati per ottenere una posizione precisa.



```java
public class DroneTelemetryFilter {
    public static void main(String[] args) {
        // --- STATO INIZIALE ---
        double positionEstimate = 0; // Dove pensiamo di essere
        double estimationError = 1;  // Quanto siamo insicuri (Incertezza)

        // --- PARAMETRI DI SISTEMA ---
        double processNoise = 0.05;  // Il vento o vibrazioni che disturbano il drone
        double sensorNoise = 0.5;    // L'errore intrinseco del sensore GPS

        // Misure grezze ricevute dal GPS (inquinate da rumore)
        double[] gpsReadings = {1.1, 2.1, 3.2, 3.9, 5.1};

        for (double measurement : gpsReadings) {
            
            // 1. FASE DI PREDIZIONE (Predict)
            // Prevediamo dove saremo basandoci sul modello fisico.
            // In questo caso statico, la posizione prevista è l'ultima nota.
            double positionPredict = positionEstimate;
            double errorPredict = estimationError + processNoise;

            // 2. CALCOLO DEL GUADAGNO DI KALMAN (K)
            // K stabilisce chi ha ragione. 
            // Se K è vicino a 1, ci fidiamo del GPS. Se è vicino a 0, della previsione.
            double kalmanGain = errorPredict / (errorPredict + sensorNoise);

            // 3. FASE DI AGGIORNAMENTO (Update)
            // Aggiorniamo la stima correggendo l'errore tra misura reale e previsione.
            positionEstimate = positionPredict + kalmanGain * (measurement - positionPredict);
            
            // Aggiorniamo l'incertezza per il prossimo ciclo
            estimationError = (1 - kalmanGain) * errorPredict;

            System.out.printf("GPS: %.2f | Stima Filtrata: %.2f | Incertezza: %.4f%n", 
                               measurement, positionEstimate, estimationError);
        }
    }
}
```

---

### Analisi Tecnica dei Parametri

Il comportamento del filtro dipende dal bilanciamento tra i due tipi di rumore. È una sfida di "fiducia" matematica.

#### 1. Rumore di Processo ($Q$ - `processNoise`)
Rappresenta quanto il modello fisico è impreciso o soggetto a disturbi esterni (es. turbolenze per un aereo).
* **Se aumenta:** Il filtro capisce che la sua "previsione" è inaffidabile. Diventerà più reattivo e seguirà molto più da vicino le misure dei sensori.
* **Se diminuisce:** Il filtro si fida ciecamente della sua logica interna. Se il sensore dà un valore errato, il filtro lo ignorerà, considerandolo un errore temporaneo.

#### 2. Rumore di Misura ($R$ - `sensorNoise`)
Rappresenta l'imprecisione dei sensori (es. la tolleranza di un termometro o l'errore del GPS).
* **Se aumenta:** Il filtro diventa "prudente". Le misure vengono filtrate pesantemente e la stima si muoverà molto lentamente, come se avesse un effetto smussato (smoothing).
* **Se diminuisce:** Il filtro crede che il sensore sia perfetto. La stima "salterà" seguendo ogni minima variazione della misura, inclusi i disturbi casuali.

#### 3. Guadagno di Kalman ($K$)
È il parametro dinamico calcolato a ogni passo.
* **$K \to 1$:** La misura è molto affidabile o il processo è molto disturbato. La correzione è massima.
* **$K \to 0$:** Il sensore è rumoroso o il modello è molto preciso. Il sistema ignora la misura e prosegue per la sua strada.

#### 4. Incertezza della Stima ($P$ - `estimationError`)
Rappresenta la fiducia del filtro nel risultato finale.
* **Cosa accade durante il ciclo:** Ad ogni iterazione, se le misure sono coerenti, l'incertezza diminuisce. Il filtro "impara" e diventa sempre più sicuro della posizione dell'oggetto, stabilizzandosi su un valore ottimale.

---

### Perché è meglio di una media?
Una media aritmetica guarda al passato in modo uguale. Il Filtro di Kalman invece vive nel presente: se improvvisamente il sensore impazzisce, il filtro se ne accorge tramite l'aumento dello scarto tra previsione e misura, adattando il guadagno $K$ per proteggere la stima finale.

Quale di questi tre algoritmi (Naive Bayes, Markov, Kalman) ti sembra più utile per un progetto di robotica? Se vuoi, possiamo approfondire come il Filtro di Kalman gestisce anche la velocità e l'accelerazione contemporaneamente.