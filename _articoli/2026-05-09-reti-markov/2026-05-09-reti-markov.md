---
layout: post
title: "Reti di Markov"
sintesi: >
Le Reti di Markov, note tecnicamente come Campi Casuali di Markov (MRF), rappresentano l'evoluzione spaziale e relazionale delle catene sequenziali.
date: 2026-05-09 07:30:17
tech: "Statistica"
tags: [Statistica, Classificazione, Reti di Markov, denoising, MRF]
---
Le **Reti di Markov**, note tecnicamente come **Campi Casuali di Markov (MRF)**, rappresentano l'evoluzione spaziale e relazionale delle catene sequenziali. Se una catena di Markov modella un processo che evolve nel tempo (come il meteo), una Rete di Markov modella un sistema di variabili che si influenzano a vicenda simultaneamente, senza un ordine cronologico.

È un modello grafico dove le connessioni non hanno una freccia: l'influenza è reciproca.

---

### Computer Vision (Restauro di Immagini)

Uno degli utilizzi più avanzati delle Reti di Markov è la **denoising**, ovvero la rimozione del rumore digitale da una fotografia. Immagina una foto scattata al buio: è piena di pixel "sporchi" (grana). 

Il computer ragiona così: un pixel non è un'entità isolata; la sua probabilità di essere di un certo colore dipende dai pixel che lo circondano (i suoi vicini). Se tutti i pixel intorno sono neri, è molto probabile che anche quel pixel granuloso debba essere nero.



```java
import java.util.Arrays;

public class MarkovNetworkDenoising {
    public static void main(String[] args) {
        // Rappresentazione semplificata di una riga di pixel di un'immagine
        // 1 = Bianco, 0 = Nero. Il valore 0.9 rappresenta rumore (dovrebbe essere 1)
        double[] noisyPixels = {1.0, 0.9, 1.0, 0.1, 0.0, 0.1};
        double[] denoisedPixels = new double[noisyPixels.length];

        // Parametro di accoppiamento (forza della rete)
        double couplingStrength = 0.8; 

        for (int i = 0; i < noisyPixels.length; i++) {
            double currentVal = noisyPixels[i];
            
            // Analisi del vicinato (Relazione spaziale)
            double neighborSum = 0;
            int neighbors = 0;

            if (i > 0) { neighborSum += noisyPixels[i-1]; neighbors++; }
            if (i < noisyPixels.length - 1) { neighborSum += noisyPixels[i+1]; neighbors++; }

            double averageNeighbor = neighborSum / neighbors;

            // Il nuovo valore è una combinazione tra il dato letto (sensore)
            // e l'influenza dei vicini (Rete di Markov)
            denoisedPixels[i] = (currentVal * (1 - couplingStrength)) + (averageNeighbor * couplingStrength);
        }

        System.out.println("Pixel originali: " + Arrays.toString(noisyPixels));
        System.out.println("Pixel filtrati:  " + Arrays.toString(denoisedPixels));
    }
}
```

---

### Analisi Tecnica dei Parametri

Nelle Reti di Markov, il comportamento è regolato da funzioni di energia e potenziali di nodo.

#### 1. Potenziale di Nodo (Dato Osservato)
Rappresenta quanto ci fidiamo della singola variabile isolata (nel codice, `currentVal`).
* **Se aumenta l'importanza:** Il sistema diventa una copia fedele dell'input originale, mantenendo però tutto il rumore e gli errori.
* **Se diminuisce:** Il sistema ignora i dati reali e si affida solo al contesto, rischiando di "inventare" informazioni o cancellare dettagli importanti.

#### 2. Potenziale di Clicca o Accoppiamento ($J_{ij}$ - `couplingStrength`)
È il parametro che definisce la forza del legame tra due nodi vicini.
* **Se aumenta:** La rete tende all'omogeneità. I nodi vicini cercheranno di essere identici tra loro. In un'immagine, questo crea un effetto "sfocatura" molto forte.
* **Se diminuisce:** La rete permette variazioni brusche tra i nodi. È utile per preservare i bordi degli oggetti in una foto, ma elimina meno rumore.

#### 3. Il Vicinato (Struttura del Grafo)
Nelle catene il vicinato è solo il "passato". Nelle reti può essere una griglia 2D o una struttura 3D.
* **Aumento del raggio di vicinato:** Il computer considera un'area più vasta per decidere lo stato di un nodo. Questo rende il calcolo molto più preciso ma aumenta esponenzialmente la complessità computazionale (servono server molto più potenti).

#### 4. Energia del Sistema ($E$)
Le Reti di Markov cercano spesso di raggiungere lo stato di "Minima Energia". 
* **Energia Alta:** Il sistema è instabile, con molte contraddizioni tra nodi vicini (es. un pixel bianco circondato da pixel neri).
* **Energia Bassa:** Il sistema è coerente e fluido. Gli algoritmi di IA lavorano per minimizzare questa energia e trovare la configurazione più probabile.

---

### Perché non usare una Catena?
Se usassimo una Catena di Markov per pulire un'immagine, il computer analizzerebbe i pixel solo da sinistra a destra. Il risultato sarebbe una scia di pixel trascinati. La **Rete di Markov** invece guarda in tutte le direzioni contemporaneamente, garantendo che ogni punto sia coerente con l'intera struttura circostante.