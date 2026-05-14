---
name: "source-command-speckit-taskstoissues"
description: "Convert existing tasks into actionable, dependency-ordered GitHub issues for the feature based on available design artifacts."
---

# source-command-speckit-taskstoissues

Use this skill when the user asks to run the migrated source command `speckit.taskstoissues`.

## Command Template

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

1. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").
1. From the executed script, extract the path to **tasks**.
1. Get the Git remote by running:

```bash
git config --get remote.origin.url
```

> [!CAUTION]
> ONLY PROCEED TO NEXT STEPS IF THE REMOTE IS A GITHUB URL

1. For each task in the list, use the GitHub MCP server to create a new issue in the repository that is representative of the Git remote.

> [!CAUTION]
> UNDER NO CIRCUMSTANCES EVER CREATE ISSUES IN REPOSITORIES THAT DO NOT MATCH THE REMOTE URL

## Codex Invocation Notes

Invoke this migrated command as `$source-command-speckit-taskstoissues` or ask Codex to run the former `speckit.taskstoissues` command. Treat `$ARGUMENTS` and `$1` placeholders as the user's text in the current request; Codex does not perform provider-side slash-command expansion. Original Claude command routing metadata is not executed by Codex, so follow this skill directly in the current session.
