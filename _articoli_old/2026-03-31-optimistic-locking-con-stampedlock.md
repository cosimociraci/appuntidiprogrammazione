---
layout: post
title: "Optimistic Locking con StampedLock"
date: 2026-03-31 10:11:47 +0200
sintesi: "Il classico ReentrantReadWriteLock può soffrire di "write starvation" se ci sono troppi lettori. StampedLock offre una modalità di lettura ottimistica..."
tech: java
tags: ['java', 'concurrency & multithreading']
---
## Esigenza Reale
Ottimizzare l'accesso a una configurazione globale caricata in memoria che viene letta da migliaia di thread al secondo ma aggiornata raramente.

## Analisi Tecnica
Problema: La contesa tra lettori e scrittori causa micro-latenze inutili in uno scenario read-heavy. Perché: Uso StampedLock. Ho scelto il lock ottimistico perché presuppongo che il dato non cambi durante la lettura; se succede, rifaccio il lavoro, evitando però di acquisire un lock reale il 99% delle volte.

## Esempio Implementativo

```java
/* Inizializzo StampedLock per gestire l'accesso alla configurazione condivisa. A differenza di ReentrantReadWriteLock, la modalità ottimistica non acquisisce alcun lock fisico: è solo un controllo di versione. */ private final StampedLock lock = new StampedLock(); private volatile AppConfig config; /* Lettura ottimistica: il caso comune, senza acquisire alcun lock. */ public AppConfig readConfig() { long stamp = lock.tryOptimisticRead(); // Ottengo il timestamp corrente AppConfig current = config; // Leggo il dato if (!lock.validate(stamp)) { // Se qualcuno ha scritto nel frattempo... /* ...scatto al lock di lettura pessimistico come fallback. Il validate() è un controllo atomico di versione: costa pochissimo. */ stamp = lock.readLock(); try { current = config; } finally { lock.unlockRead(stamp); } } return current; } /* Scrittura: acquisisco il lock esclusivo. Le scritture sono rare, quindi il costo è accettabile. */ public void updateConfig(AppConfig newConfig) { long stamp = lock.writeLock(); try { this.config = newConfig; } finally { lock.unlock(stamp); } } /* Uso in Spring Boot: registro questo componente come @Bean singleton e lo inietto nei service che accedono alla configurazione. L'accesso è thread-safe senza synchronized e senza bloccare i lettori. */ @Component public class ConfigHolder { private final StampedLock lock = new StampedLock(); private volatile AppConfig config = AppConfig.defaults(); public AppConfig get() { long stamp = lock.tryOptimisticRead(); AppConfig c = config; if (!lock.validate(stamp)) { stamp = lock.readLock(); try { c = config; } finally { lock.unlockRead(stamp); } } return c; } public void set(AppConfig newConfig) { long stamp = lock.writeLock(); try { this.config = newConfig; } finally { lock.unlock(stamp); } } } /* Attenzione: StampedLock NON è rientrante. Se lo stesso thread tenta di acquisire il writeLock due volte, va in deadlock. Usarlo solo in metodi brevi e non rientranti. */
```