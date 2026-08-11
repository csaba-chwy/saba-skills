# generate-service-description

This repository contains the `generate-service-description` Codex skill.

## Install

This repo is currently meant to be installed manually rather than via the GitHub skill installer.

Clone it into your Codex skills directory with the skill folder name `generate-service-description`:

```bash
git clone <skill-repository-url> ~/.codex/skills/generate-service-description
```

Then restart Codex so it reloads skills.

## Requirements

The machine running this skill needs:

- `codex`
- `git`
- access to the repository you want to inspect

## What It Does

Given a repository, the skill inspects the code and runtime configuration, identifies the main API or job surface area and integrations, and writes or refreshes a concise repo-local `service_description.md`. When the file already exists, the skill updates it in place by removing stale information, replacing changed behavior with current facts from the code, preserving still-accurate sections, and updating `Last verified: YYYY-MM-DD` to the current review date.

## When To Use It

- You need a concise `service_description.md` for a service or application repo.
- You want a repo summary grounded in code and config rather than naming guesses.
- You want a lightweight document that helps future agents and developers quickly judge scope and impact.

## Repository Structure

- `SKILL.md`: canonical instructions and workflow
- `agents/openai.yaml`: skill metadata for the Codex UI
- `references/`: rubric and guidance for the generated document

## Notes

- The skill is optimized for short, evidence-based summaries rather than exhaustive documentation.
- It writes or updates exactly one repo-local `service_description.md` unless the user asks for more.
- This repo should live at `~/.codex/skills/generate-service-description` unless you manage your Codex skills directory differently.

## Canonical Documentation

See [SKILL.md](./SKILL.md) for the full workflow and operating rules.

This README is intentionally brief so `SKILL.md` remains the single source of truth.
