# Deployment

## Docker Compose

```bash
docker compose up --build
```

The compose file uses a named volume for persistent data and exposes the server on `WORKLEDGER_PORT` or `8000` by default.

If `WORKLEDGER_API_KEY` is set, all non-health endpoints require `Authorization: Bearer <key>`.
