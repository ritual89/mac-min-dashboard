# Spec 05 — Auto-Promote Rules

| Field | Value |
|-------|-------|
| Status | **Approved** |
| Source | PLAN.md §5 |
| Author | mac-mini-dashboard |

## Context

Discovery finds workloads; promotion rules decide which appear on the main dashboard without manual YAML entries.

## Functional Requirements

- **FR-1:** Workloads start as `discovered`; promotion sets `monitored=true`.
- **FR-2:** MUST auto-promote when: kind is `docker` or `compose`; project path under configured roots; listening port > 1024 not in denylist; name/label in allowlist.
- **FR-3:** MUST NOT promote: launchd labels matching `com.apple.*`; paths under `/usr`, `/System`, `/bin`, `/sbin`.
- **FR-4:** Manual pin MUST force `monitored=true` regardless of rules.
- **FR-5:** Manual unpin MUST set `monitored=false` and clear pin flag.

## Acceptance Criteria

- **AC-5.1:** Given docker workload, when promote evaluated, then promoted.
- **AC-5.2:** Given compose workload under `~/dev/myproject`, when roots include `~/dev`, then promoted.
- **AC-5.3:** Given port 3000 listener not in denylist, then promoted.
- **AC-5.4:** Given allowlist contains `hermes` and workload name `hermes`, then promoted.
- **AC-5.5:** Given launchd label `com.apple.SomeService`, then NOT promoted.
- **AC-5.6:** Given path `/usr/local/bin/app`, then NOT promoted.
- **AC-5.7:** Given pinned workload failing all rules, then still monitored.
- **AC-5.8:** Given unpinned workload matching no rules, then not monitored.

## Edge Cases

- **EC-5.1:** Port 1024 exactly — NOT promoted (must be > 1024).
- **EC-5.2:** Tilde in roots expanded via host home — use path as configured for v1.

## Out of Scope

- ML-based promotion
- Per-workload mute
