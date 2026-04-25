---
layout: code
title: "CQRS (Command Query Responsibility Segregation)"
date: 2026-07-13 12:00:00
sintesi: >
  Usare lo stesso modello per leggere e scrivere dati porta a compromessi sulle performance. La separazione tra Command (scrive/modifica) e Query (legge) permette di ottimizzare i Command per la consistenza e le Query per la velocità (es. usando viste 
tech: "javascript"
tags: ["javascript", "postgresql"]
pdf_file: "cqrs-command-query-responsibility-segregation.pdf"
---

## Esigenza Reale
Scalare un'applicazione social dove la frequenza di lettura (feed) è 1000x superiore a quella di scrittura (post).

## Analisi Tecnica
**Problema:** Modelli di dati troppo complessi che tentano di soddisfare sia i vincoli di validazione che le esigenze di reportistica veloce.

**Perché:** Separo le responsabilità. Ho scelto CQRS per poter scalare i database di lettura indipendentemente dai servizi di scrittura, ottimizzando i tempi di risposta delle API.

## Esempio Implementativo

```javascript
/* LATO COMMAND: gestisco le operazioni di scrittura con validazione e
    invarianti di dominio. */
class CreatePostCommand {
    constructor({
        authorId, content, tags
    }
    ) {
        // Validazione delle invarianti del dominio: avviene sul lato Command,
            non sul lato Query if (!authorId) throw new Error('authorId è
            obbligatorio')
        ;
        if (!content || content.trim().length < 10) throw new Error('Il
            contenuto deve avere almeno 10 caratteri');
        if (content.length > 5000) throw new Error('Il contenuto non può
            superare 5000 caratteri');
        this.authorId = authorId;
        this.content = content.trim();
        this.tags = tags ?? [];
        this.createdAt = new Date();
    }
}
class PostCommandHandler {
    constructor(writeDb, eventBus) {
        this.writeDb = writeDb;
        // Database ottimizzato per scritture (es. PostgreSQL normalizzato)
            this.eventBus = eventBus
        ;
    }
    async handle(command) {
        if (command instanceof CreatePostCommand) {
            // Salvo nel write model: schema normalizzato, ottimizzato per
                integrità const post = await this.writeDb.posts.create(
            {
                authorId: command.authorId, content: command.content, tags:
                    command.tags, createdAt: command.createdAt
            }
            );
            // Pubblico l'evento per aggiornare le read views in modo asincrono
                await this.eventBus.publish('POST_CREATED',
            {
                postId: post.id, authorId: post.authorId, content: post.content,
                    tags: post.tags, createdAt: post.createdAt
            }
            );
            return post.id;
        }
        throw new Error('Command non gestito: ' + command.constructor.name);
    }
}
/* LATO QUERY: gestisco le letture con modelli de-normalizzati ottimizzati per
    la UI. */
class FeedQueryHandler {
    constructor(readDb) {
        // Database di lettura: può essere Redis, Elasticsearch, MongoDB o una
            vista materializzata this.readDb = readDb
        ;
    }
    async getFeed(userId, {
        page = 1, limit = 20
    }
    = {
    }
    ) {
        // Query ultra-veloce su una vista pre-calcolata: nessun JOIN, nessuna
            logica di dominio
        return this.readDb.feedViews.find({
            targetUserId: userId, page, limit
        }
        );
        // Ritorna direttamente il DTO pronto per la UI
    }
    async getPostById(postId) {
        return this.readDb.postDetails.findOne({
            id: postId
        }
        );
        // Vista denormalizzata: autore, like count, commenti in una sola query
    }
    async searchPosts(query, tags) {
        // Elasticsearch ottimizzato per full-text search: impossibile sul write
            model normalizzato
        return this.readDb.searchIndex.query({
            text: query, tags
        }
        );
    }
}
/* Sincronizzo i read models tramite event listener: aggiornamento asincrono
    delle viste. */
class FeedProjection {
    constructor(readDb) {
        this.readDb = readDb;
    }
    // Questo handler viene invocato ogni volta che POST_CREATED viene
        pubblicato async onPostCreated(event)
    {
        // Recupero i follower dell'autore e aggiorno la loro feed view const
            followers = await this.readDb.follows.findFollowers(event.authorId)
        ;
        // Fan-out: aggiorno la feed view di ogni follower await
            Promise.all(followers.map(followerId =>
            this.readDb.feedViews.insert(
        {
            targetUserId: followerId, postId: event.postId, authorId:
                event.authorId, contentPreview: event.content.substring(0, 200),
                tags: event.tags, createdAt: event.createdAt
        }
        ) ));
    }
}
/* Assemblo tutto in Express: Command e Query su endpoint separati. */
const commandHandler = new PostCommandHandler(writeDb, eventBus);
const queryHandler = new FeedQueryHandler(readDb);
// READ: ottimizzato per velocità, può essere cachato a più livelli
    app.get('/feed', async (req, res) =>
{
    const feed = await queryHandler.getFeed(req.user.id, req.query);
    res.json(feed);
    // Risposta in < 10ms dalla vista pre-calcolata
}
);
// WRITE: ottimizzato per consistenza e validazione app.post('/posts', async
    (req, res) =>
{
    const command = new CreatePostCommand({
        authorId: req.user.id, ...req.body
    }
    );
    const postId = await commandHandler.handle(command);
    res.status(202).json({
        postId, message: 'Post creato. Il feed verrà aggiornato a breve.'
    }
    );
}
);
```
