---
layout: post
title: "Object Pooling per Risorse Native"
date: 2027-07-28 12:00:00
sintesi: >
  Creare oggetti Java è veloce, ma creare risorse che toccano il sistema operativo (connessioni DB, contesti crittografici, buffer off-heap) è estremamente costoso. Il pooling non va abusato per i POJO (il GC è più efficiente), ma è obbligatorio per og
tech: "java"
tags: ["java", "memory & performance"]
pdf_file: "object-pooling-per-risorse-native.pdf"
---

## Esigenza Reale
Gestire un alto volume di messaggi cifrati dove l'inizializzazione del motore di cifratura richiede millisecondi preziosi.

## Analisi Tecnica
**Problema:** Latenza elevata dovuta alla continua creazione e distruzione di oggetti che allocano memoria nativa o socket.
**Perché:** Uso un pool di oggetti. Ho scelto di pre-allocare queste risorse pesanti per trasformare un costo di inizializzazione in un semplice "checkout" da una coda concorrente.

## Esempio Implementativo

```java
/* Implemento un pool robusto usando Apache Commons Pool2, che gestisce
    nativamente la validazione, l'eviction degli oggetti scaduti e il
    dimensionamento dinamico. */
public class CipherEngineFactory extends BasePooledObjectFactory<Cipher> {
    @Override public Cipher create() throws Exception {
        // Inizializzazione costosa: eseguita solo quando il pool è vuoto Cipher
            cipher = Cipher.getInstance("AES/GCM/NoPadding")
        ;
        log.debug("Creato nuovo Cipher engine: pool era esaurito");
        return cipher;
    }
    @Override public PooledObject<Cipher> wrap(Cipher cipher) {
        return new DefaultPooledObject<>(cipher);
    }
    @Override public boolean validateObject(PooledObject<Cipher> p) {
        // Verifico che l'oggetto sia ancora usabile prima di darlo in prestito
        return p.getObject() != null;
    }
    @Override public void passivateObject(PooledObject<Cipher> p) {
        // Resetto lo stato prima di restituire al pool (pulizia dell'IV/nonce
            usato) p.getObject().getParameters()
        ;
        // Force state reset
    }
}
@Service public class EncryptionService {
    private final GenericObjectPool<Cipher> pool;
    public EncryptionService() {
        GenericObjectPoolConfig<Cipher> config = new
            GenericObjectPoolConfig<>();
        config.setMaxTotal(20);
        // Massimo 20 cipher engine contemporaneamente config.setMaxIdle(10)
        ;
        // Mantengo 10 pronti in standby config.setMinIdle(5)
        ;
        // Pre-alloco 5 all'avvio config.setMaxWait(Duration.ofSeconds(2))
        ;
        // Timeout se il pool è esaurito config.setTestOnBorrow(true)
        ;
        // Valido l'oggetto prima del checkout this.pool = new
            GenericObjectPool<>(new CipherEngineFactory(), config)
        ;
    }
    public byte[] encrypt(byte[] data, SecretKey key) throws Exception {
        Cipher cipher = pool.borrowObject();
        // Checkout: se il pool è vuoto aspetto max 2s try
        {
            byte[] iv = generateIv();
            cipher.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(128,
                iv));
            return cipher.doFinal(data);
        }
        finally {
            pool.returnObject(cipher);
            // Sempre nel finally: garantito anche in caso di eccezione
        }
    }
    /* Espongo le metriche del pool tramite Micrometer per monitorare il
        dimensionamento: */
    @Bean public MeterBinder cipherPoolMetrics() {
        return registry -> {
            Gauge.builder("cipher.pool.active", pool,
                GenericObjectPool::getNumActive) .description("Cipher engine in
                uso").register(registry);
            Gauge.builder("cipher.pool.idle", pool,
                GenericObjectPool::getNumIdle) .description("Cipher engine
                disponibili").register(registry);
            Gauge.builder("cipher.pool.waiters", pool,
                GenericObjectPool::getNumWaiters) .description("Thread in attesa
                di un Cipher").register(registry);
        }
        ;
    }
}
```
