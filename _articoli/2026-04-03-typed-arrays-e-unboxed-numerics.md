---
layout: post
title: "Typed Arrays e Unboxed Numerics"
date: 2026-04-03 14:44:48
sintesi: >
  In JS standard, i numeri sono solitamente allocati nell'heap come 'Boxed Doubles'. Per il calcolo intensivo, gli array standard [] introducono overhead di puntatori. Float64Array o Int32Array allocano un blocco di memoria continua (C-style), permette
tech: "js"
tags: ["js", "v8 engine & runtime performance"]
pdf_file: "typed-arrays-e-unboxed-numerics.pdf"
---

## Esigenza Reale
Implementare un motore di calcolo per segnali audio o manipolazione di pixel in tempo reale nel browser o Node.js.

## Analisi Tecnica
Problema: Latenza computazionale e picchi di GC causati dall'allocazione continua di numeri ad alta precisione in array dinamici. Perché: Uso i Typed Arrays. Ho scelto questa struttura per forzare il runtime a usare memoria fissa e contigua, permettendo ottimizzazioni SIMD e un accesso ai dati estremamente più veloce.

## Esempio Implementativo

```js
/* Confronto il costo tra Array standard e Typed Array per renderlo concreto. */
 
// APPROCCIO SBAGLIATO: Array standard con Boxed Doubles const standardArray =
// new Array(1_000_000); for (let i = 0; i < standardArray.length; i++)
{ standardArray[i] = Math.random(); 
// Ogni numero è un oggetto HeapNumber sull'heap V8 }
 
// Operazione su array standard: V8 deve unboxare ogni elemento const sum1 =
// standardArray.reduce((acc, v) => acc + v, 0);
// APPROCCIO CORRETTO: Float64Array con memoria contigua const typedArray = new
// Float64Array(1_000_000); for (let i = 0; i < typedArray.length; i++)
{ typedArray[i] = Math.random(); 
// Scrittura diretta in memoria C-style: zero boxing }
 
// Operazione su Typed Array: V8 usa SIMD e accesso diretto ai double let sum2 =
// 0; for (let i = 0; i < typedArray.length; i++)
{ sum2 += typedArray[i]; 
// Loop ottimizzato con istruzioni vettoriali dalla CPU }
 
/* Scelgo il tipo corretto in base al dominio del problema: */
 
// Float64Array: calcolo scientifico, audio (range completo double IEEE 754) 
// Float32Array: grafica 3D, WebGL (meno preciso ma 2x più compatto) 
// Int32Array: contatori, indici, coordinate pixel 
// Uint8Array: buffer raw, dati di rete, immagini (RGBA) 
// Uint8ClampedArray: manipolazione pixel canvas (clamping automatico 0-255) 
* Implemento un equalizzatore audio con Typed Arrays per elaborazione real-time:
* */
 class AudioEqualizer 
{ constructor(sampleRate, bufferSize) 
{ this.sampleRate = sampleRate; this.bufferSize = bufferSize; 
// Pre-alloco tutti i buffer una sola volta: zero GC pressure durante
// l'elaborazione this.inputBuffer = new Float32Array(bufferSize);
// this.outputBuffer = new Float32Array(bufferSize); this.coefficients = new
// Float64Array(10);
// 10 bande equalizzatore }
 applyEq(inputData) 
{ 
// Copio i dati in ingresso nel buffer pre-allocato: zero nuove allocazioni
// this.inputBuffer.set(inputData);
// Applico i filtri: operazioni puramente numeriche su memoria contigua for (let
// i = 0; i < this.bufferSize; i++)
{ let sample = this.inputBuffer[i]; for (let band = 0; band < 10; band++) 
{ sample *= this.coefficients[band]; }
 this.outputBuffer[i] = Math.max(-1, Math.min(1, sample)); 
// Clamping }
 return this.outputBuffer; 
// Ritorno il buffer pre-allocato: zero copie }
 }
 
* Per la manipolazione di pixel con Canvas API, uso Uint8ClampedArray tramite
* ImageData: */
 function applyBrightnessFilter(canvas, brightness) 
{ const ctx = canvas.getContext('2d'); const imageData = ctx.getImageData(0, 0,
canvas.width, canvas.height); const pixels = imageData.data;
// Uint8ClampedArray: RGBA per ogni pixel 
// Itero sui pixel: ogni gruppo di 4 byte è un pixel RGBA for (let i = 0; i <
// pixels.length; i += 4)
{ pixels[i] = pixels[i] + brightness; 
// R: il clamping 0-255 è automatico pixels[i + 1] = pixels[i + 1] + brightness;
// G pixels[i + 2] = pixels[i + 2] + brightness; 
// B 
// pixels[i + 3]: Alpha non modificato }
 ctx.putImageData(imageData, 0, 0); }
 
/* Per trasferire Typed Arrays tra Worker e Main Thread senza copiare: */
 const sharedBuffer = new SharedArrayBuffer(Float64Array.BYTES_PER_ELEMENT *
1_000_000); const sharedArray = new Float64Array(sharedBuffer);
// Sia main thread che worker accedono allo stesso sharedArray: zero copie, zero
// GC worker.postMessage(
{ buffer: sharedBuffer }
); 
// SharedArrayBuffer è condiviso, non trasferito
```
