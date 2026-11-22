# Worker de retención (F1)

El worker de F1 reutiliza el paquete de la API para no duplicar modelos,
configuración ni acceso a S3:

- Código: [`services/api/app/worker.py`](../api/app/worker.py).
- Contenedor: `issitek-worker` en [`infra/docker-compose.yml`](../../infra/docker-compose.yml).
- Comando: `python -m app.worker`.
- Purga grabaciones con `deleted_at` o `retention_until <= now`, elimina el
  objeto y anonimiza `storage_key` como `purged/{id}`.
- Escribe un heartbeat en `/tmp/issitek-worker-heartbeat` para el healthcheck.
- Variables: `WORKER_INTERVAL_SECONDS` (3600), `WORKER_RUN_ONCE` (false),
  `RECORDING_RETENTION_DAYS` (30).

Cuando el worker crezca (reconciliación de huérfanos, métricas, colas), se
separará a su propio paquete en F4a.
