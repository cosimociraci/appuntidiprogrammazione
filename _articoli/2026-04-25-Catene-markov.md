---
layout: code
title: "Catene di Markov"
date: 2026-04-25 07:25:10
sintesi: >
    Le Catene di Markov sono modelli matematici utilizzati per descrivere una sequenza di eventi in cui la probabilità di passare a uno stato futuro dipende esclusivamente dallo stato attuale. Questo principio è noto come Proprietà di Markov (o "assenza di memoria").
tech: "Statistica"
tags: ["statistica"]
---
## Catene di Markov

Le Catene di Markov sono modelli matematici utilizzati per descrivere una sequenza di eventi in cui la probabilità di passare a uno stato futuro dipende esclusivamente dallo stato attuale. Questo principio è noto come **Proprietà di Markov** (o "assenza di memoria").

In ambito professionale, questo concetto non serve solo a prevedere il meteo, ma è fondamentale per:
1.  **Algoritmi di Ranking (come PageRank di Google):** Per determinare l'importanza di una pagina web in base ai link che riceve.
2.  **Modelli di Linguaggio (LLM):** Per prevedere la parola successiva in una frase.
3.  **Sistemi di Manutenzione Predittiva:** Per calcolare quando un macchinario industriale passerà dallo stato "funzionante" allo stato "guasto".

---

### Manutenzione di un Server

In questo esempio, analizziamo il comportamento di un server aziendale. Il sistema può trovarsi in due stati: **Operativo** o **In Errore**.



```java
import java.util.Random;

public class ServerStabilityMonitor {
    public static void main(String[] args) {
        Random random = new Random();

        // Stato iniziale: 0 = Operativo, 1 = In Errore
        int currentState = 0; 

        // Simulazione di un ciclo di 24 ore
        for (int hour = 0; hour < 24; hour++) {
            String statusReport = (currentState == 0) ? "OPERATIVO" : "ERRORE SISTEMA";
            System.out.println("Ora " + hour + ": " + statusReport);

            double threshold = random.nextDouble();

            if (currentState == 0) {
                // Probabilità di restare Operativo: 95%
                // Probabilità di crash: 5%
                currentState = (threshold < 0.95) ? 0 : 1;
            } else {
                // Probabilità di autoriparazione: 20%
                // Probabilità di restare in Errore: 80%
                currentState = (threshold < 0.20) ? 0 : 1;
            }
        }
    }
}
```

---

### Parametri dell'Algoritmo: Analisi Tecnica

Nelle Catene di Markov, i parametri principali sono le **Probabilità di Transizione**. Vediamo come influenzano il comportamento del sistema.

#### 1. Probabilità di Permanenza ($P_{ii}$)
Rappresenta la probabilità che il sistema rimanga nello stato attuale (es. da Operativo a Operativo).
* **Se aumenta verso 1.0:** Il sistema diventa statico. I cambiamenti sono rarissimi e il modello tende a "bloccarsi" nello stato iniziale.
* **Se diminuisce verso 0.0:** Il sistema diventa instabile. Il computer passerà continuamente da uno stato all'altro ad ogni iterazione.

#### 2. Probabilità di Transizione ($P_{ij}$)
Rappresenta la probabilità di cambiare stato (es. da Operativo a Errore).
* **Se aumenta:** Il sistema è guidato verso una direzione specifica. Se la probabilità di passare da "Errore" a "Operativo" è alta, il sistema dimostra una forte capacità di resilienza o recupero.
* **Se diminuisce:** Lo stato diventa una "trappola". Se la probabilità di uscire dallo stato di "Errore" è vicina allo zero, quel punto viene definito **Stato Assorbente**: una volta entrati, non si esce più.

#### 3. Lo Stato Iniziale ($S_0$)
* **Impatto a breve termine:** Determina i primi risultati della simulazione. Se il server parte in "Errore", i primi cicli rifletteranno questa condizione critica.
* **Impatto a lungo termine:** In molti modelli (chiamati Ergodici), l'importanza dello stato iniziale diminuisce nel tempo. Dopo migliaia di passaggi, il sistema raggiungerà una **Distribuzione Stazionaria**, dove la probabilità di trovarsi in uno stato dipende solo dalle percentuali di transizione e non da come è iniziata la simulazione.

#### 4. Numero di Iterazioni (Ciclo for)
* **Aumento delle iterazioni:** Permette di osservare il comportamento statistico reale del sistema. Con poche iterazioni il risultato è casuale; con migliaia di iterazioni si ottiene una stima precisa dell'affidabilità del sistema nel tempo.

---

### La Matrice di Transizione
In un contesto tecnico avanzato, questi parametri non vengono gestiti con dei semplici `if`, ma inseriti in una **Matrice di Transizione**. Questa struttura dati permette di calcolare stati futuri molto distanti (es. tra 100 giorni) utilizzando l'algebra lineare invece di una simulazione passo-dopo-passo.