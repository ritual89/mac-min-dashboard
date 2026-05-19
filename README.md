# mac-min-dashboard

Mac Mini homelab dashboard project with project-level [Cursor Agent Skills](https://cursor.com/docs/agent/skills) sourced from [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills).

## Skills

Engineering-focused curated set (not the full 313-skill library):

- `engineering-team/` — core engineering roles (architecture, frontend, backend, DevOps, QA, security, etc.)
- `engineering/` — advanced engineering (CI/CD, observability, RAG, MCP, reliability, etc.)

Upstream pin: **v2.8.0** (see `skills.lock.json`). Currently **129** skills installed.

### Install or refresh skills

```bash
./scripts/install-skills.sh
```

Requires `git`. Clones upstream into `vendor/claude-skills/` (gitignored) and copies skills into `.cursor/skills/`.

### Verify

```bash
find .cursor/skills -name SKILL.md | wc -l
python3 .cursor/skills/*/scripts/*.py --help 2>/dev/null | head -1 || true
```

In Cursor, open this folder; skills under `.cursor/skills/` load automatically for the project.

### Security audit (optional)

```bash
git clone --depth 1 --branch v2.8.0 https://github.com/alirezarezvani/claude-skills.git /tmp/claude-skills-audit
for skill in .cursor/skills/*/; do
  python3 /tmp/claude-skills-audit/engineering/skill-security-auditor/scripts/skill_security_auditor.py "$skill" || true
done
```

## License

Application code: TBD. Bundled skills follow the upstream [MIT license](https://github.com/alirezarezvani/claude-skills/blob/main/LICENSE).
