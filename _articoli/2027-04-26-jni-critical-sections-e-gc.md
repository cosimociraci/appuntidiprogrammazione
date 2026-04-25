---
layout: code
title: "JNI Critical Sections e GC"
date: 2027-04-26 12:00:00
sintesi: >
  Quando il codice nativo JNI è in esecuzione, il GC potrebbe aver bisogno di spostare gli oggetti nell'heap, ma non può farlo se il C sta usando i puntatori (pinning). Il rischio è bloccare il GC (Stop-The-World prolungato) a causa di thread nativi "l
tech: "java"
tags: ["java", "garbage collector"]
pdf_file: "jni-critical-sections-e-gc.pdf"
---

## Esigenza Reale
Risolvere problemi di pause GC estreme in applicazioni che usano pesantemente calcoli matriciali in C.

## Analisi Tecnica
**Problema:** Il Garbage Collector non riesce a terminare i cicli perché i thread JNI tengono "bloccato" l'heap.

**Perché:** Uso le sezioni critiche solo per operazioni atomiche. Ho scelto di minimizzare il tempo speso con i puntatori "critici" per garantire che la JVM possa eseguire i suoi compiti di manutenzione senza ritardi.

## Esempio Implementativo

```java
/* PATTERN SBAGLIATO: la sezione critica dura troppo a lungo e congela il GC. */
JNIEXPORT void JNICALL Java_MatrixService_multiplyBad(JNIEnv* env, jobject obj,
    jintArray a, jintArray b, jintArray result) {
    jint* dataA = (*env)->GetPrimitiveArrayCritical(env, a, NULL);
    jint* dataB = (*env)->GetPrimitiveArrayCritical(env, b, NULL);
    // SBAGLIATO: operazione O(n^3) dentro la sezione critica // Il GC è
        bloccato per tutta la durata del calcolo! for (int i = 0
    ;
    i < N;
    i++) for (int j = 0;
    j < N;
    j++) for (int k = 0;
    k < N;
    k++) result_data[i*N+j] += dataA[i*N+k] * dataB[k*N+j];
    (*env)->ReleasePrimitiveArrayCritical(env, a, dataA, JNI_ABORT);
    (*env)->ReleasePrimitiveArrayCritical(env, b, dataB, JNI_ABORT);
}
/* PATTERN CORRETTO con Panama: uso MemorySegment per eliminare completamente il
    problema. Panama non fa pinning dell'heap perché lavora su memoria off-heap:
    il GC è sempre libero di muovere gli oggetti Java. */
@Service public class MatrixMultiplicationService {
    private final MethodHandle matrixMultiplyHandle;
    public int[] multiply(int[] matrixA, int[] matrixB, int n) throws Throwable
        {
        try (Arena arena = Arena.ofConfined()) {
            // Copio i dati in memoria off-heap: nessun pinning dell'heap Java
                MemorySegment segA = arena.allocateFrom(ValueLayout.JAVA_INT,
                matrixA)
            ;
            MemorySegment segB = arena.allocateFrom(ValueLayout.JAVA_INT,
                matrixB);
            MemorySegment segResult = arena.allocate((long) n * n *
                ValueLayout.JAVA_INT.byteSize());
            // Il C lavora su memoria nativa: il GC è completamente libero
                durante il calcolo matrixMultiplyHandle.invokeExact(segA, segB,
                segResult, n)
            ;
            return segResult.toArray(ValueLayout.JAVA_INT);
        }
    }
}
/* Se sono costretto a usare JNI legacy, minimizzo il tempo della sezione
    critica copiando i dati fuori dalla sezione prima del calcolo: */
JNIEXPORT void JNICALL Java_MatrixService_multiplyCorrect(JNIEnv* env, jobject
    obj, jintArray a, jintArray b, jsize n) {
    // Alloco buffer C temporanei jint* localA = (jint*)malloc(n * n *
        sizeof(jint))
    ;
    jint* localB = (jint*)malloc(n * n * sizeof(jint));
    jint* localResult = (jint*)calloc(n * n, sizeof(jint));
    /* Sezione critica MINIMA: solo la copia dei dati, non il calcolo */
    jint* dataA = (*env)->GetPrimitiveArrayCritical(env, a, NULL);
    memcpy(localA, dataA, n * n * sizeof(jint));
    // Copia veloce (*env)->ReleasePrimitiveArrayCritical(env, a, dataA,
        JNI_ABORT)
    ;
    // Rilascio IMMEDIATO jint* dataB = (*env)->GetPrimitiveArrayCritical(env,
        b, NULL)
    ;
    memcpy(localB, dataB, n * n * sizeof(jint));
    (*env)->ReleasePrimitiveArrayCritical(env, b, dataB, JNI_ABORT);
    // Il calcolo avviene FUORI dalla sezione critica: GC libero di girare
        matrix_multiply(localA, localB, localResult, n)
    ;
    /* Scrittura risultato: altra sezione critica minima */
    jintArray result = (*env)->NewIntArray(env, n * n);
    jint* resultData = (*env)->GetPrimitiveArrayCritical(env, result, NULL);
    memcpy(resultData, localResult, n * n * sizeof(jint));
    (*env)->ReleasePrimitiveArrayCritical(env, result, resultData, 0);
    free(localA);
    free(localB);
    free(localResult);
}
/* Monitoro le pause GC causate da JNI in produzione tramite JFR: */
// jcmd <PID> JFR.start name=gc_jni settings=profile // Filtro per eventi "GC
    Pause" con causa "JNI Critical Section"
```
