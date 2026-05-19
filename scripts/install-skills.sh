#!/usr/bin/env bash
# Install curated Cursor skills from alirezarezvani/claude-skills (see skills.lock.json).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TAG="v2.8.0"
REPO_URL="https://github.com/alirezarezvani/claude-skills.git"
VENDOR="vendor/claude-skills"
BUNDLES=(engineering-team engineering)
DEST=".cursor/skills"

if [[ ! -d "${VENDOR}/.git" ]]; then
  echo "Cloning ${REPO_URL} @ ${TAG} ..."
  mkdir -p vendor
  git clone --depth 1 --branch "${TAG}" "${REPO_URL}" "${VENDOR}"
else
  echo "Syncing ${VENDOR} @ ${TAG} ..."
  git -C "${VENDOR}" fetch --depth 1 origin "refs/tags/${TAG}" 2>/dev/null || true
  git -C "${VENDOR}" checkout "${TAG}" 2>/dev/null || true
fi

echo "Installing skills into ${DEST}/ ..."
rm -rf "${DEST}"
mkdir -p "${DEST}"

for bundle in "${BUNDLES[@]}"; do
  echo "  Bundle: ${bundle}"
  while IFS= read -r skill_md; do
    skill_dir="$(dirname "${skill_md}")"
    name="$(basename "${skill_dir}")"
    target="${DEST}/${name}"
    if [[ -e "${target}" ]]; then
      parent="$(basename "$(dirname "${skill_dir}")")"
      target="${DEST}/${parent}-${name}"
    fi
    cp -R "${skill_dir}" "${target}"
  done < <(find "${VENDOR}/${bundle}" -name SKILL.md -type f)
done

count="$(find "${DEST}" -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')"
echo "Done. ${count} skill(s) in ${DEST}/"
