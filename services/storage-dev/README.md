# Almacenamiento S3 de desarrollo

Este contenedor **no es MinIO**: es [moto](https://github.com/getmoto/moto) en
modo servidor, un emulador S3 para desarrollo y pruebas.

## Por qué

MinIO archivó su edición comunitaria y ya no distribuye binarios ni imágenes
(`dl.min.io` responde 410; los registros devuelven 401). La API de Issitek
Language usa el **cliente S3** (`minio-py`), así que el mismo código funciona
contra cualquier servicio S3-compatible.

## Producción

Antes de producción hay que decidir el proveedor definitivo (MinIO si se
consigue una imagen/registro autorizado, Garage, SeaweedFS o un S3 gestionado)
y apuntar `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY` y `MINIO_SECRET_KEY` a ese
servicio. **No usar moto en producción**: no persiste datos ni aplica las
garantías de un almacenamiento real.

## Comprobación rápida

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:9100/
```
