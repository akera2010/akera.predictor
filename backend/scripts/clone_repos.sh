#!/usr/bin/env bash
# Clone the optional third-party prediction repos listed in
# akeraten/models/extra_repos.json into backend/external_repos/ (git-ignored).
# Each one then needs a small akeraten_adapter.py exposing
#   predict_match(player_a, player_b, surface, tournament) -> float | None
# (see akeraten/models/repos/base.py). Check each repo's licence before use.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p external_repos
python - <<'PY' | while read -r name url; do
import json
for r in json.load(open("akeraten/models/extra_repos.json")):
    if "github.com" in r["repo"]:
        print(r["name"], r["repo"])
PY
  if [ -d "external_repos/$name/.git" ]; then
    echo "updating $name"; git -C "external_repos/$name" pull --ff-only || true
  else
    echo "cloning $url"; git clone --depth 1 "$url" "external_repos/$name" || echo "  ! could not clone $url"
  fi
done
echo "HTTP-based models (e.g. tennis-oracle-api on Hugging Face) are not cloned: set TENNIS_ORACLE_URL instead."
