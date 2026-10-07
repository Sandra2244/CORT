#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
while IFS='|' read -r name url; do
  [[ -z "$name" || "$name" == \#* ]] && continue
  [[ "$url" == *REEMPLAZAR* ]] && { echo "Salto $name: edita scripts/upstreams.txt"; continue; }
  [[ -d "upstream/$name" ]] && { echo "$name ya existe"; continue; }
  git clone --depth 1 "$url" "upstream/$name"
done < scripts/upstreams.txt
