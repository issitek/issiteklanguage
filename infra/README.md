# Infraestructura de Issitek Language

Proyecto Compose **independiente** (`issitek-language`). No comparte red,
volúmenes, nombres de contenedor ni secretos con otros proyectos del VPS.

## Puertos (host)

| Servicio | Puerto | Notas |
|---|---|---|
| Web (nginx) | **8090** | SPA + proxy `/api` al API |
| API | **8000** | `http://localhost:8000/docs` |
| Postgres | **5433** | usuario/DB `issitek` / `issitek_language` |
| Redis | **6380** | reservado para F2/F4a |
| Almacenamiento S3 | **9100** | moto en desarrollo |
| Kokoro (opcional) | **9083** | solo con `docker-compose.kokoro.yml` |

`80` y `443` quedan libres para el proxy del host.

## Almacenamiento: decisión pendiente

MinIO archivó su edición comunitaria y ya no distribuye binarios ni imágenes
(`dl.min.io` responde 410; los registros devuelven 401). Por eso el servicio
`storage` de desarrollo usa **moto** (emulador S3), no MinIO.

La API habla S3 mediante `minio-py`, así que cambiar de proveedor es solo
configuración (`MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`). Antes
de producción hay que decidir el destino definitivo: MinIO con una imagen
autorizada, Garage, SeaweedFS o un S3 gestionado. **moto no sirve en
producción** (no persiste ni garantiza durabilidad).

### URLs firmadas

`MINIO_ENDPOINT` es el host interno (contenedor → contenedor). Las URLs que ve
el navegador usan `MINIO_PUBLIC_ENDPOINT`; en desarrollo es
`localhost:8090/s3` y nginx las reenvía a `storage:9000` conservando el `Host`
firmado. Así la subida y la reproducción son del mismo origen y no necesitan
CORS. En producción, apuntar `MINIO_PUBLIC_ENDPOINT` al endpoint S3 público.

Ver [`services/storage-dev/README.md`](../services/storage-dev/README.md).

## Arranque

```bash
cd infra
cp .env.example .env
# editar .env: contraseñas y JWT_SECRET
docker compose up -d --build
docker compose ps
curl -s http://localhost:8000/health
curl -s http://localhost:8000/health/ready
```

Abrir `http://localhost:8090`, crear una cuenta y recorrer la lección 1.

El `entrypoint` de la API ejecuta `alembic upgrade head` y el seed idempotente
del curso A1 (10 lecciones) antes de arrancar Uvicorn.

`issitek-worker` reutiliza el paquete de la API (`python -m app.worker`) para
purgar grabaciones vencidas o revocadas, eliminar el objeto de S3 y anonimizar
la referencia. Por defecto corre cada hora (`WORKER_INTERVAL_SECONDS=3600`) y
publica un heartbeat para su healthcheck. Detalle en
[`services/worker/README.md`](../services/worker/README.md).

nginx resuelve `api` y `storage` con el DNS interno de Docker en cada petición,
así que recrear solo un contenedor no deja respuestas 502 por una IP vieja.

## TTS

- `TTS_PROVIDER=fake` (por defecto): genera un tono corto para que la vertical
  slice funcione sin Kokoro. **No es audio pedagógico.**
- `TTS_PROVIDER=kokoro`: usa Kokoro por el endpoint `/v1/audio/speech`.
  Para levantarlo dentro del proyecto (CPU, descarga el modelo la primera vez):

```bash
docker compose -f docker-compose.yml -f docker-compose.kokoro.yml up -d --build
```

La API queda en `TTS_LOCAL_URL=http://tts:8880` y el contenedor publica
`127.0.0.1:9083` solo para depuración (`KOKORO_PORT`). Para pregenerar el audio
de las 10 lecciones:

```bash
docker compose -f docker-compose.yml -f docker-compose.kokoro.yml exec api \
  python scripts/pregenerate_tts.py
```

- El laboratorio puede seguir usando su propio Kokoro en `9082`; no se comparte
  con el Compose del producto.

## Pruebas

La API necesita Postgres y el almacenamiento S3. Con los servicios arriba:

```bash
cd services/api
uv venv --python 3.12
uv pip install -r requirements-dev.txt
createdb -h localhost -p 5433 -U issitek issitek_test   # una vez
DATABASE_URL=postgresql+psycopg://issitek:issitek@localhost:5433/issitek_test \
MINIO_ENDPOINT=localhost:9100 \
MINIO_ACCESS_KEY=issitek MINIO_SECRET_KEY=issitek-secret \
  uv run pytest -q
```

O dentro de Docker (imagen con dependencias de test):

```bash
cd infra
docker build --build-arg INSTALL_DEV=true -t issitek-api:test ../services/api
docker run --rm --network issitek_net \
  -e DATABASE_URL=postgresql+psycopg://issitek:issitek@postgres:5432/issitek_test \
  -e MINIO_ENDPOINT=storage:9000 \
  -e MINIO_ACCESS_KEY=issitek -e MINIO_SECRET_KEY=issitek-secret \
  issitek-api:test pytest -q
```

## Contrato compartido, frontend y E2E

```bash
pnpm install
pnpm typecheck                  # @issitek/shared + @issitek/web
pnpm shared:generate            # openapi.d.ts desde packages/shared/openapi.json
pnpm build
```

Para actualizar el snapshot OpenAPI después de cambiar la API:

```bash
cd services/api
. .venv/bin/activate
python scripts/export_openapi.py
cd ../..
pnpm shared:generate
```

El E2E usa Chromium con micrófono sintético (`apps/web/e2e/fixtures/hello.wav`)
y requiere el stack arriba en `http://localhost:8090`:

```bash
pnpm exec playwright install chromium
pnpm test:e2e
```

## Datos y limpieza

```bash
docker compose down          # conserva volúmenes
docker compose down -v       # borra Postgres y Redis (irreversible)
```

Los volúmenes se llaman `issitek_pgdata` e `issitek_redis`. Las grabaciones de
desarrollo viven en moto (en memoria) y se pierden al reiniciar; en producción
irán al almacenamiento S3 definitivo.
