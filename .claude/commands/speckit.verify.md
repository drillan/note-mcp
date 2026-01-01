---
description: Verify the consistency between implemented code and design artifacts (spec, plan, tasks) for the current feature branch.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Perform a **read-only**, comprehensive audit of the currently implemented code against the project's specification and design documents. The goal is to detect implementation bugs, deviations from the spec, and design ambiguities before the feature is considered complete.

## Operating Constraints

1.  **READ-ONLY**: Do **not** modify any files (code or docs).
2.  **Strict Prerequisite**: This command **MUST ABORT** if `tasks.md` does not exist OR if zero tasks are marked as completed (`[x]`).
3.  **Scope**: Focus ONLY on the tasks marked as completed in `tasks.md` and their corresponding code. Do not hallucinate errors for unstarted tasks.

## Execution Steps

### 1. Prerequisite Check & Context Loading

1.  Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` to get paths.
2.  **Task Status Validation**:
    *   Parse `tasks.md`.
    *   Count total tasks and completed tasks (marked with `[x]` or `[X]`).
    *   **CRITICAL**: If completed tasks count is **0**, output: "⛔ **ABORT**: No tasks have been marked as completed in `tasks.md`. Please run `/speckit.implement` or manually mark tasks as done before verifying." and **STOP execution**.
3.  **Load Artifacts**:
    *   Read `spec.md` (Requirements, User Stories, Edge Cases).
    *   Read `plan.md` (Architecture, Tech Stack).
    *   Read `data-model.md` (Entities).
    *   Read `quickstart.md` (Integration Scenarios & Usage Examples).
    *   Read ALL files under the `contracts/` directory.
    *   Read `tasks.md` (to identify which files have been modified/created).

### 2. Codebase Analysis (Targeted)

1.  **Get Branch Diff**: Run `git diff main...HEAD --name-only` to get the cumulative list of changed files on this feature branch. This is the authoritative source of what has been modified.
2.  **Read Code**: For each changed file, load its content. Also run `git diff main...HEAD` to see the actual changes (additions, deletions, modifications).
3.  **Cross-reference with Tasks**: Compare the changed files against file paths mentioned in completed tasks within `tasks.md`. Flag any discrepancies (files changed but not mentioned in tasks, or tasks mentioning files not actually changed).
4.  **Traceability Mapping**:
    *   Map Task ID → Functional Requirement (FR-XXX) directly by analyzing task descriptions and referencing `spec.md`.
    *   For each completed task, identify which FR(s) it implements.

### 3. Verification Logic

Perform a deep analysis comparing the **Code** against the **Docs**. Check for:

#### A. Implementation Integrity (Code vs. Spec)
*   **Functionality**: For each Functional Requirement (FR-XXX) related to completed tasks, verify that the **input → processing → effect** causal chain is established in the code. "Code exists" is insufficient—confirm that inputs defined in the requirement are processed and produce the expected effects through traceable code paths.
    *   **Verification procedure**:
        1.  Extract the **input** (config values, parameters, user inputs) mentioned in the FR.
        2.  Trace where this input is **read** in the code.
        3.  Trace how the input **affects processing** (conditionals, calculations, method calls).
        4.  Confirm the **expected effect** (output, state change, behavior) occurs as a result.
        5.  If any link in the chain is broken (e.g., input defined but never read), report as **CRITICAL**.
*   **Data Integrity**: Perform **bidirectional** comparison between code and `data-model.md`:
    *   (Doc → Code): Every field/entity in `data-model.md` exists in the implementation with correct name, type, and constraints.
    *   (Code → Doc): Every field/entity in the implementation is documented in `data-model.md` (no undocumented additions).
*   **API Compliance**: Do the implemented endpoints/interfaces match the definitions found in **all `contracts/` files**?
*   **Usage Consistency**: Does the code align with the usage examples provided in `quickstart.md`?
*   **Edge Cases**: Does the code handle the "Edge Cases" listed in `spec.md`? (e.g., error handling, null states).

#### B. Design Consistency (Spec vs. Plan vs. Code)
*   **Architecture**: Does the code follow the structure defined in `plan.md`?
*   **Ambiguity**: Did the implementation require guessing because the Spec was vague?
*   **Omissions**: Using the Task → FR mapping from Step 2.3, check if any FR associated with a completed task is only **partially implemented**. An FR is partially implemented if some of its sub-requirements or conditions are missing from the code.

### 4. Report Generation

Output a **Concise Verification Report**. Do not dump raw logs. Use the structure below.

---

## Verification Report: [FEATURE NAME]

**Status**: [PASS / FAIL / WARN]
**Progress**: [X]/[Y] Tasks Verified

### 1. Critical Discrepancies (Action Required)
*Report issues from: **Functionality**, **Data Integrity**, **API Compliance**, **Usage Consistency**, **Omissions**.*

| Severity | Component/File | Issue | Spec Reference |
| :--- | :--- | :--- | :--- |
| **CRITICAL** | `src/models/user.ts` | Missing `email` validation field required by data model. | `data-model.md` Entity: User |
| **HIGH** | `src/api/auth.py` | Error 401 returns HTML instead of JSON. | `contracts/openapi.yaml` |
| **HIGH** | `src/cli/main.py` | CLI arguments do not match the example commands. | `quickstart.md` |

*(If none, display "✅ No critical implementation discrepancies found.")*

### 2. Specification & Design Gaps
*Report issues from: **Architecture**, **Ambiguity**.*

*   **[Ambiguity]**: The spec didn't define the max file size for uploads. Implemented as 5MB default. Is this correct?
*   **[Inconsistency]**: `plan.md` called for PostgreSQL, but code uses SQLite syntax in migration files.

### 3. Code Quality & Edge Cases
*Report issues from: **Edge Cases**.*

*   **Edge Case Coverage**: [High/Medium/Low] - *Brief comment (e.g., "Null checks present, but timeout handling missing").*
*   **Test Coverage Check**: *Do tests exist for the completed files? Do they cover the FR requirements?*

### 4. Recommendations
*   [Short bullet point on what to fix in code]
*   [Short bullet point on what to update in spec/plan]

---

## Final Instruction

If **CRITICAL** issues are found, advise the user to fix the code or update the spec before proceeding.
If only **Spec Gaps** are found, advise running `/speckit.clarify` or updating the spec manually.
If **PASS**, confirm the implementation is solid so far.