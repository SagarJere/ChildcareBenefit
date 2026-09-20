# docker/

Reserved for shared Docker assets that are not specific to a single service
(for example, a reverse-proxy configuration fronting both the frontend and
backend containers in a later increment).

Each service currently owns its own `Dockerfile` (`backend/Dockerfile`,
`frontend/Dockerfile`) and the local development stack is defined in the
root `docker-compose.yml`.
