#!/usr/bin/env bash
# publicar.sh — republica lab/web-grabador/ en la rama `pages` (GitHub Pages)
# Uso: ./publicar.sh [mensaje]
# Requiere: origin git@github.com:issitek/issiteklanguage.git con acceso SSH.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP=$(mktemp -d /tmp/grabador-pages.XXXXXX)
trap 'rm -rf "$TMP"' EXIT

git clone --quiet --branch pages git@github.com:issitek/issiteklanguage.git "$TMP"
cp "$HERE"/{index.html,app.js,codec.js,style.css,README.md} "$TMP"/
cd "$TMP"

if git diff --quiet; then
  echo "Sin cambios; no hay nada que publicar."
  exit 0
fi

git add .
git -c user.name=Angel -c user.email=angelip56@gmail.com commit --quiet -m "${1:-pages: actualización del grabador estático}"
git push --quiet origin pages
echo "Publicado. Verifica: curl -sI https://issitek.github.io/issiteklanguage/ | head -3"
