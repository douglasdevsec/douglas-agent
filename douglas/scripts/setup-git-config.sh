#!/usr/bin/env bash
# Configura el driver de merge que protege los assets de marca de Douglas
# Agent contra ser pisados por `git merge upstream/main`.
#
# Por qué hace falta: la config de un driver de merge vive en .git/config,
# que NO se versiona. .gitattributes (sí versionado) declara QUÉ archivos
# usan el driver `keepours`, pero el driver en sí solo existe si esto se
# ejecuta una vez por clon. Sin este paso, git usa su estrategia de merge
# por defecto y un cambio de upstream en esos archivos SÍ puede pisar la
# versión de Douglas Agent (ver douglas/README.md, "Proteger los assets
# de marca").
#
# Uso:
#   ./douglas/scripts/setup-git-config.sh

set -euo pipefail

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "error: no estás dentro de un repositorio git" >&2
  exit 1
fi

git config merge.keepours.driver true

echo "[ok] merge.keepours.driver configurado en .git/config (local a este clon)."
echo "     Verifica con: git config --get merge.keepours.driver"
