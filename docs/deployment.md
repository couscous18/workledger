# Deployment

## Docker Compose

```bash
docker compose up --build
```

The compose file uses a named volume for persistent data and exposes the server on `WORKLEDGER_PORT` or `8000` by default.

By default, non-health endpoints stay disabled until you set `WORKLEDGER_API_KEY`.

For local-only experiments, you can opt into open access explicitly with `WORKLEDGER_ALLOW_UNAUTHENTICATED_API=true`, but that should not be used for exposed deployments.
