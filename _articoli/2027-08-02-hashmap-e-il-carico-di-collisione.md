---
layout: code
title: "HashMap e il carico di collisione"
date: 2027-08-02 12:00:00
sintesi: >
  Quando molti oggetti hanno lo stesso hashCode, le performance della HashMap degradano da O(1) a O(n) (o O(log n) in Java 8+ grazie ai TreeNode). Monitorare la distribuzione dei bucket nelle mappe critiche è essenziale. Per chiavi custom, l'hashCode d
tech: "java"
tags: ["java", "concurrency"]
pdf_file: "hashmap-e-il-carico-di-collisione.pdf"
---

## Esigenza Reale
Prevenire rallentamenti critici in una cache in memoria che gestisce milioni di voci con chiavi composite.

## Analisi Tecnica
**Problema:** Degradazione delle performance di ricerca nelle mappe dovuta a una cattiva distribuzione degli hash delle chiavi.

**Perché:** Ottimizzo il metodo hashCode. Ho scelto di implementare una distribuzione uniforme per assicurarmi che i dati siano sparsi correttamente tra i bucket della mappa, minimizzando le collisioni.

## Esempio Implementativo

```java
/* Implemento un hashCode di qualità per una chiave composita. Il coefficiente
    31 è un numero primo che massimizza la distribuzione dei bit e viene
    ottimizzato dal JIT in shift + subtract. */
public final class CacheKey {
    private final String tenantId;
    private final String resourceType;
    private final long resourceId;
    private final int hash;
    // Cache del hash: calcolato una sola volta, la chiave è immutabile public
        CacheKey(String tenantId, String resourceType, long resourceId)
    {
        this.tenantId = tenantId;
        this.resourceType = resourceType;
        this.resourceId = resourceId;
        // Calcolo il hash nel costruttore: evito di rifarlo ad ogni put/get
            nella HashMap this.hash = computeHash()
        ;
    }
    private int computeHash() {
        int h = 17;
        // Primo diverso da 0 come seed h = 31 * h + (tenantId != null ?
            tenantId.hashCode() : 0)
        ;
        h = 31 * h + (resourceType != null ? resourceType.hashCode() : 0);
        h = 31 * h + Long.hashCode(resourceId);
        // Long.hashCode fa XOR dei 32 bit alti con i 32 bassi
        return h;
    }
    @Override public int hashCode() {
        return hash;
        // Lettura del campo: nessun calcolo
    }
    @Override public boolean equals(Object obj) {
        if (this == obj) return true;
        if (!(obj instanceof CacheKey other)) return false;
        return resourceId == other.resourceId && Objects.equals(tenantId,
            other.tenantId) && Objects.equals(resourceType, other.resourceType);
    }
}
/* Verifico la distribuzione del hash su un campione reale di chiavi: */
@Test public void verifyHashDistribution() {
    int buckets = 1024;
    int[] distribution = new int[buckets];
    List<CacheKey> keys = generateSampleKeys(100_000);
    for (CacheKey key : keys) {
        int bucket = (key.hashCode() ^ (key.hashCode() >>> 16)) & (buckets - 1);
        distribution[bucket]++;
    }
    // Calcolo il coefficiente di variazione: deve essere < 10% per una buona
        distribuzione double mean =
        Arrays.stream(distribution).average().orElse(0)
    ;
    double variance = Arrays.stream(distribution) .mapToDouble(v -> Math.pow(v -
        mean, 2)).average().orElse(0);
    double cv = Math.sqrt(variance) / mean;
    assertTrue(cv < 0.1, "Distribuzione hash scarsa: CV=" + cv + " (atteso <
        0.1)");
}
/* Configuro la HashMap con il load factor e la capacità iniziale corretti per
    evitare rehashing: */
@Component public class ResourceCache {
    // Capacità iniziale = dimensione attesa / load factor, arrotondata alla
        potenza di 2 più vicina // Per 1 milione di entry con load factor 0.75:
        1_000_000 / 0.75 = 1_333_333 -> 2^21 = 2_097_152 private final
        Map<CacheKey, Resource> cache = new HashMap<>(2_097_152, 0.75f)
    ;
    /* Se il numero di entry è noto a priori, uso questo calcolo per evitare il
        rehashing costoso: */
    public static int optimalInitialCapacity(int expectedSize) {
        return (int) Math.ceil(expectedSize / 0.75) + 1;
    }
}
/* Per mappe con altissima concorrenza in lettura, uso ConcurrentHashMap con
    parallelismThreshold appropriato: */
private final ConcurrentHashMap<CacheKey, Resource> concurrentCache = new
    ConcurrentHashMap<>(optimalInitialCapacity(1_000_000), 0.75f, 32);
// 32 segmenti di concorrenza /* Individuo le HashMap con collisioni eccessive
    in produzione tramite JFR: nell'evento "Object Allocation in New TLAB"
    filtro per java.util.HashMap$TreeNode: se appaiono, significa che alcuni
    bucket hanno degenerato in alberi rosso-neri per troppe collisioni. */
```
