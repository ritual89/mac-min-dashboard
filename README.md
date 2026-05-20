# mac-mini-dashboard

Mac Mini homelab dashboard project with project-level [Cursor Agent Skills](https://cursor.com/docs/agent/skills) sourced from [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills).

## Default persona: Solo Founder

Every Cursor session in this repo uses the **Solo Founder** persona by default (pragmatic, time-aware, anti–scope-creep). Adapted from [agents/personas/solo-founder.md](https://github.com/alirezarezvani/claude-skills/blob/main/agents/personas/solo-founder.md).

| File | Role |
|------|------|
| `.cursor/rules/solo-founder.mdc` | Always-on rule (`alwaysApply: true`) |
| `.cursor/agents/solo-founder.md` | Full persona reference |

To disable temporarily, turn off the rule in Cursor Settings → Rules, or set `alwaysApply: false` in the `.mdc` file.

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
