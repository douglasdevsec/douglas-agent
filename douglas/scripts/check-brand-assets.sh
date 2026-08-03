#!/usr/bin/env bash
# Revisión post-merge de assets de marca. Corre esto después de cualquier
# `git merge upstream/main`.
#
# Por qué NO basta con `git status --short` después del merge: el driver
# `keepours` (ver .gitattributes + setup-git-config.*) resuelve el conflicto
# de binario DURANTE el merge y deja el árbol de trabajo limpio — el commit
# de merge ya incluye nuestra versión. `git status` no muestra nada raro
# aunque upstream haya intentado cambiar el archivo; hace falta comparar
# contra lo que upstream trajo realmente.
#
# Qué hace este script:
#   1. Si HEAD es un commit de merge (2 padres), toma automáticamente
#      "nuestro lado" (HEAD^1) y "el lado de upstream" (HEAD^2).
#   2. Calcula el merge-base entre ambos.
#   3. Para cada extensión de imagen relevante bajo los directorios de
#      marca, lista qué archivos cambió o añadió el lado de upstream desde
#      el merge-base.
#   4. Marca cada uno como "protegido" (está en .gitattributes, el driver
#      debió conservar nuestra versión) o "⚠ NO PROTEGIDO" (upstream pudo
#      haber colado un archivo nuevo o uno que no está en la lista).
#
# Uso:
#   douglas/scripts/check-brand-assets.sh                # usa HEAD^1/HEAD^2
#   douglas/scripts/check-brand-assets.sh <ours> <theirs> # explícito

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

BRAND_DIRS=(
  "assets"
  "apps/desktop/assets"
  "apps/desktop/public"
  "apps/desktop/src/assets/brand"
  "apps/bootstrap-installer/src/assets/brand"
  "apps/bootstrap-installer/src-tauri/icons"
)
IMAGE_EXT_PATTERN='\.(png|svg|ico|icns|jpg|jpeg|webp)$'

if [ "$#" -ge 2 ]; then
  OURS="$1"
  THEIRS="$2"
else
  PARENTS=$(git log -1 --format='%P' HEAD)
  # shellcheck disable=SC2206
  PARENTS_ARR=($PARENTS)
  if [ "${#PARENTS_ARR[@]}" -ne 2 ]; then
    echo "error: HEAD no es un commit de merge (2 padres) — pasa <ours> <theirs> explícitamente." >&2
    echo "  ej: douglas/scripts/check-brand-assets.sh HEAD~1 upstream/main" >&2
    exit 1
  fi
  OURS="${PARENTS_ARR[0]}"
  THEIRS="${PARENTS_ARR[1]}"
fi

MERGE_BASE="$(git merge-base "$OURS" "$THEIRS")"

echo "[check-brand-assets] ours=$OURS theirs=$THEIRS merge-base=$MERGE_BASE"
echo ""

CHANGED=$(git diff --name-status "$MERGE_BASE" "$THEIRS" -- "${BRAND_DIRS[@]}" | grep -E "$IMAGE_EXT_PATTERN" || true)

if [ -z "$CHANGED" ]; then
  echo "[ok] upstream no tocó ni añadió ninguna imagen bajo los directorios de marca en este merge."
  exit 0
fi

echo "Upstream modificó o añadió estos archivos de imagen bajo directorios de marca:"
echo ""

FOUND_UNPROTECTED=0

while IFS=$'\t' read -r status path; do
  [ -z "$path" ] && continue
  if git check-attr merge -- "$path" | grep -q "merge: keepours"; then
    protected="protegido (driver keepours debió conservar nuestra versión — verifica igual)"
  else
    protected="⚠ NO PROTEGIDO — revisar manualmente, no está en .gitattributes"
    FOUND_UNPROTECTED=1
  fi
  printf '  [%s] %s\n      %s\n' "$status" "$path" "$protected"
done <<< "$CHANGED"

echo ""
if [ "$FOUND_UNPROTECTED" -eq 1 ]; then
  echo "⚠ Hay al menos un archivo sin protección — revísalo antes de dar el merge por bueno."
  echo "  Si es un asset de marca nuevo, añádelo a .gitattributes (ver 'assets de marca' en douglas/README.md)."
  exit 1
fi

echo "Todos los archivos tocados por upstream están en la lista protegida."
