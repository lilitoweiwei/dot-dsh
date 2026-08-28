---
name: editing-skills
description: Use when creating, changing, or validating a skill for this harness — writing or editing a SKILL.md bundle or flat Markdown skill, choosing which root to store it in, setting invocation policy, or diagnosing why a skill is not discovered.
---

# Editing skills

A skill is a reusable set of task-specific instructions stored as Markdown and loaded into the session on demand. Creating one is a plain file write: the watcher picks it up automatically — no restart, no registration step.

## Where skills live

Roots are scanned in this rank order (lower rank wins a name conflict):

| Rank | Root | Use for |
|---|---|---|
| 100 | `<projectRoot>/.dsh/skills` | one project's skills; projectRoot is the nearest ancestor with `.git`, else the session cwd |
| 200 | `<projectRoot>/.agents/skills` | project-scoped, shared-agent variant |
| 300 | `customSkillDirs` (preset config) | skills that travel with a preset (cordis pattern, `baseUrl`-relative) |
| 400 | `<dshHome>/skills` (`~/.dsh/skills`) | **default choice**: personal skills visible to every skill-enabled preset |
| 500 | `<agentsHome>/skills` (`~/.agents/skills`) | machine-shared agent skills |
| 600 | `$DSH_BUNDLED_SKILL_DIR` | app-bundled skills (unset on this machine) |

`<dshHome>/skills` skips a `.system` child. Only sessions whose preset mounts `skill-filesystem` and `tool-skill` ever receive a catalog, so a teaching skill in the user root reaches only skill-enabled agents.

## Format

- A skill is a directory bundle `<name>/SKILL.md` or a flat `<name>.md`, directly under a root. Discovery is ONE level deep — nested `**/SKILL.md` is never found.
- `name` must be kebab-case: `^[a-z0-9]+(?:-[a-z0-9]+)*$`.
- Frontmatter (open YAML) requires `name` and `description`; optional keys: `whenToUse`, `metadata`, `disable-model-invocation`, `user-invocable`.
- Invocation fields accept YAML booleans and `true/false/yes/no/on/off/1/0`; omitted means allowed on that surface. An invalid value drops the entire skill with a warning — policy fails closed.
- `disable-model-invocation: true` hides the skill from the model catalog; `user-invocable: false` hides it from the human `/name` menu.

## How changes surface

- New skill or frontmatter change → a replacement catalog message at the next model pre-step; the model sees the new entry immediately.
- Body-only edits are re-read on each load; they change later results without a catalog message.
- A malformed skill disappears from the catalog with a warning — the model cannot tell "absent" from "broken". When a skill does not show up, check: kebab-case name, one-level depth, valid frontmatter, correct root, and that the preset mounts the skill rows.
- The user can load a skill by typing `/name` in the GUI; the model loads via the `skill` tool. When a skill body has already been injected into the conversation, follow it without calling the `skill` tool again.
