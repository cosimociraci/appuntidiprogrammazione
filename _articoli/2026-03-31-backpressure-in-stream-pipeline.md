---
layout: post
title: "Backpressure in Stream Pipeline"
date: 2026-03-31 18:54:40 
sintesi: "Leggere dati più velocemente di quanto si riesca a scriverli causa il riempimento del buffer (RAM). Il segnale di "backpressure" indica al readable di fermarsi finché il writable non ha svuotato il suo buffer. L'uso di stream.pipeline() invece di .pi"
tech: js
tags: [js, "node.js internals & libuv"]
pdf_file: "backpressure-in-stream-pipeline.pdf"
---

## Esigenza Reale
Trasferire file di diversi gigabyte tra un client e un server senza esaurire la memoria RAM del processo Node.js.

## Analisi Tecnica
Problema: OutOfMemoryError causato dall'accumulo di chunk di dati nel buffer di scrittura (writable.write() restituisce false). Perché: Implemento il controllo del flusso. Ho scelto pipeline perché mette in pausa il "Readable" finché il "Writable" non ha terminato di svuotare il buffer verso il kernel (drain).

## Esempio Implementativo

```js
/* Dimostro il problema della backpressure non gestita con .pipe() manuale. */ // SBAGLIATO: nessuna gestione della backpressure const readable = fs.createReadStream('huge-file.zip'); const writable = fs.createWriteStream('output.zip'); readable.on('data', chunk => { const canContinue = writable.write(chunk); // Se false, il buffer di writable è pieno if (!canContinue) { readable.pause(); // Devo mettere in pausa manualmente writable.once('drain', () => readable.resume()); // Riprendo quando il buffer si svuota } }); // Questo è esattamente quello che pipeline() fa automaticamente /* CORRETTO: uso pipeline() con async/await per gestione automatica della backpressure ed errori. */ const { pipeline } = require('stream/promises'); const fs = require('fs'); const zlib = require('zlib'); async function transferLargeFile(inputPath, outputPath) { console.log(`Trasferimento di ${inputPath} -> ${outputPath}`); const start = Date.now(); try { await pipeline( fs.createReadStream(inputPath, { highWaterMark: 64 * 1024 }), // 64KB chunk size zlib.createGzip({ level: 6 }), // Comprimo in-stream: zero file intermedi fs.createWriteStream(outputPath) // pipeline gestisce pause/resume automaticamente ); const elapsed = ((Date.now() - start) / 1000).toFixed(2); console.log(`Completato in ${elapsed}s`); } catch (err) { console.error('Pipeline fallita:', err.message); // pipeline chiude automaticamente tutti gli stream in caso di errore: zero fd leak throw err; } } /* Implemento uno stream Transform personalizzato per manipolare i dati in pipeline: */ const { Transform } = require('stream'); class CsvToJsonTransform extends Transform { constructor() { super({ readableObjectMode: true, // Output: oggetti JS writableObjectMode: false // Input: Buffer/string }); this._headers = null; this._buffer = ''; } _transform(chunk, encoding, callback) { this._buffer += chunk.toString(); const lines = this._buffer.split('
'); this._buffer = lines.pop(); // Tengo l'ultima riga incompleta per il prossimo chunk for (const line of lines) { if (!line.trim()) continue; if (!this._headers) { this._headers = line.split(',').map(h => h.trim()); } else { const values = line.split(','); const obj = {}; this._headers.forEach((header, i) => { obj[header] = values[i]?.trim(); }); this.push(obj); // push() rispetta la backpressure automaticamente } } callback(); // Segnalo che ho finito di processare questo chunk } _flush(callback) { // Processo l'eventuale ultima riga senza newline finale if (this._buffer.trim() && this._headers) { const values = this._buffer.split(','); const obj = {}; this._headers.forEach((header, i) => { obj[header] = values[i]?.trim(); }); this.push(obj); } callback(); } } /* Pipeline completa: leggo CSV da 10GB, trasformo in JSON, salvo senza caricare nulla in RAM. */ async function processMassiveCsv(inputPath, outputPath) { const jsonStream = fs.createWriteStream(outputPath); jsonStream.write('[
'); let isFirst = true; const objectWriter = new Transform({ objectMode: true, transform(obj, _, cb) { const prefix = isFirst ? '' : ',
'; isFirst = false; cb(null, prefix + JSON.stringify(obj)); } }); await pipeline( fs.createReadStream(inputPath), new CsvToJsonTransform(), objectWriter, jsonStream ); fs.appendFileSync(outputPath, '
]'); } /* In Express, uso pipeline per servire file grandi senza caricarli in memoria: */ app.get('/download/:filename', async (req, res) => { const filePath = path.join(UPLOADS_DIR, req.params.filename); const stat = fs.statSync(filePath); res.setHeader('Content-Length', stat.size); res.setHeader('Content-Type', 'application/octet-stream'); try { await pipeline(fs.createReadStream(filePath), res); } catch (err) { if (err.code !== 'ERR_STREAM_PREMATURE_CLOSE') { console.error('Errore download:', err); } } });
```
