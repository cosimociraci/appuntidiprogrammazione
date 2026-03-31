---
layout: post
title: "Synchronous Commit & Performance Trade-off"
date: 2026-03-31 17:04:42 
sintesi: "La replica sincrona garantisce che una transazione sia confermata solo dopo essere stata scritta su almeno un nodo standby. Questo elimina il rischio di perdere dati in caso di failover, ma introduce una latenza pari al Round Trip Time (RTT) tra i se"
tech: db
tags: ['db', 'advanced replication & ha']
pdf_file: "synchronous-commit-performance-trade-off.pdf"
---

## Esigenza Reale
Proteggere le transazioni finanziarie critiche garantendo che siano scritte su due server prima di rispondere "OK" all'utente.

## Analisi Tecnica
Problema: L'overhead della rete rallenta ogni singola scrittura se configurato globalmente in modalità sincrona. Perché: Uso la configurazione granulare. Ho scelto di impostare la sincronia solo per le sessioni che gestiscono bilanci economici, lasciando le altre transazioni in modalità asincrona per massimizzare il throughput.

## Esempio Implementativo

```db
/* Configuro il nodo standby come sincrono nel postgresql.conf del Master: */ -- synchronous_standby_names = 'FIRST 1 (standby1, standby2)' /* Nella sessione critica del pagamento forzo la replica sincrona al livello più alto: remote_apply garantisce che la transazione sia non solo ricevuta ma anche applicata sulla replica prima del commit. */ SET synchronous_commit = 'remote_apply'; BEGIN; UPDATE accounts SET balance = balance - 100 WHERE id = 1; UPDATE accounts SET balance = balance + 100 WHERE id = 2; INSERT INTO payment_audit (amount, from_account, to_account, ts) VALUES (100, 1, 2, now()); COMMIT; /* La risposta "OK" arriva al client solo dopo che la replica ha applicato queste righe. Il costo è il doppio RTT di rete ma la garanzia è assoluta. */ /* Per i log applicativi non critici, uso off: Postgres scrive nel WAL buffer locale e risponde subito, accettando il rischio di perdere al massimo gli ultimi 3 WAL segment in caso di crash. */ SET synchronous_commit = 'off'; INSERT INTO app_logs (level, message, created_at) VALUES ('INFO', 'User logged in', now()); /* Riepilogo dei livelli disponibili e delle loro garanzie: off -> nessuna garanzia, massima velocità local -> scritto nel WAL locale, non sulla replica remote_write -> WAL ricevuto dalla replica ma non scritto su disco remote_apply -> WAL applicato sulla replica (massima garanzia) */ /* In Spring Boot, uso due DataSource separati con configurazioni diverse: */ @Bean @Primary public DataSource primaryDataSource() { HikariConfig config = new HikariConfig(); config.setConnectionInitSql("SET synchronous_commit = 'remote_apply'"); return new HikariDataSource(config); } @Bean @Qualifier("loggingDataSource") public DataSource loggingDataSource() { HikariConfig config = new HikariConfig(); config.setConnectionInitSql("SET synchronous_commit = 'off'"); return new HikariDataSource(config); } /* Nel servizio di pagamento uso il DataSource primario con replica sincrona, nel servizio di logging uso quello asincrono: */ @Service public class PaymentService { @Autowired @Primary private JdbcTemplate primaryJdbc; // synchronous_commit = remote_apply @Transactional public void transfer(long from, long to, BigDecimal amount) { primaryJdbc.update("UPDATE accounts SET balance = balance - ? WHERE id = ?", amount, from); primaryJdbc.update("UPDATE accounts SET balance = balance + ? WHERE id = ?", amount, to); } }
```
