# Fastify v4 — Server (本地缓存副本, 来源 https://fastify.dev/docs/v4.x/Reference/Server.md)

## server.listen()

When not using a custom port, `server.listen()` returns a Promise that
resolves once the server is ready; you should await it before issuing
requests.
