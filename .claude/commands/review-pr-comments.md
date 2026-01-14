---
description: Review and respond to code review comments from automated reviewers (AI bots, linters, etc.)
---

## User Input

```text
$ARGUMENTS
```

**Required**: PR number (e.g., `45`)

## Goal

Evaluate code review comments from automated reviewers, decide which to accept or reject, implement fixes, and respond appropriately.

## Execution Steps

### Step 1: Fetch Review Comments

Use `gh` CLI to get review threads and comments. **Important**: Two different ID formats are needed:

1. **Thread ID** (GraphQL node_id like `PRRT_xxx`): Used for resolving threads
2. **Comment ID** (REST API numeric like `2604837472`): Used for replying to comments

**Step 1a: Get repository information**

First, get the owner and repository name. **Do NOT guess these values** - always retrieve them using the command below:

```bash
gh repo view --json owner,name --jq '"\(.owner.login)/\(.name)"'
```

Use the output (e.g., `drillan/note-mcp`) for `{owner}` and `{repo}` in subsequent commands.
Replace placeholders: `{owner}` → `drillan`, `{repo}` → `note-mcp`.

```bash
# Step 1b: Get thread IDs (for resolving) via GraphQL
gh api graphql -f query='
query {
  repository(owner: "{owner}", name: "{repo}") {
    pullRequest(number: $ARGUMENTS) {
      reviewThreads(first: 50) {
        nodes {
          id
          isResolved
          path
          line
          comments(first: 10) {
            nodes {
              body
              author { login }
            }
          }
        }
      }
    }
  }
}'

# Step 1c: Get numeric comment IDs (for replying) via REST API
gh api repos/{owner}/{repo}/pulls/$ARGUMENTS/comments --jq '.[] | "\(.id) \(.path):\(.line) \(.user.login)"'
```

Filter for unresolved threads from automated reviewers (bots, AI assistants, linters).

**ID Mapping Example**:
| Thread ID (GraphQL) | Comment ID (REST) | File |
|---------------------|-------------------|------|
| PRRT_kwDOQZ9YJM5lbGiX | 2604837472 | Dockerfile:117 |

### Step 2: Evaluate Each Comment

For each comment, evaluate using these criteria:

| Criterion | Accept if... | Reject if... |
|-----------|-------------|--------------|
| **Environment** | Applies to production/security-critical code | Development-only, no security impact |
| **Practicality** | Easy to implement, clear benefit | Impractical or requires major refactoring |
| **Cost/Benefit** | High value, low effort | Low value, high effort |
| **Philosophy** | Aligns with project's simplicity principles | Over-engineering, premature optimization |

### Step 3: Create Response Plan

Output a table summarizing decisions:

| Thread ID | File | Issue | Decision | Action |
|-----------|------|-------|----------|--------|
| PRRT_xxx | path/file.py | Description | ✅ Accept / ❌ Reject | Fix / Reply+Resolve |

### Step 4: For REJECTED Comments - Reply and Resolve

**Important**: Use the correct ID format for each operation:
- **Reply**: Use **numeric comment ID** from REST API (e.g., `2604837472`)
- **Resolve**: Use **thread ID** from GraphQL (e.g., `PRRT_kwDOQZ9YJM5lbGiX`)

```bash
# Reply to the comment (use NUMERIC comment ID from REST API)
gh api repos/{owner}/{repo}/pulls/$ARGUMENTS/comments/{numeric_comment_id}/replies \
  -f body='Thank you for the suggestion. After evaluation:

[REASON]

This is acceptable for our use case because [SPECIFIC REASON].

Resolving this conversation.'

# Resolve the thread (use THREAD ID from GraphQL)
gh api graphql -f query='
mutation {
  resolveReviewThread(input: {threadId: "PRRT_xxx"}) {
    thread { isResolved }
  }
}'
```

### Step 5: For ACCEPTED Comments - Implement Fixes

1. Read the affected files
2. Make the necessary changes
3. Verify changes don't break anything (`make -C dockerfiles/dev quality-gate-fast` or equivalent)

### Step 6: Summarize in PR Comment

```bash
gh pr comment $ARGUMENTS --body "## Code Review Response

### Addressed
- ✅ [Description of fix 1]
- ✅ [Description of fix 2]

### Declined (with rationale)
- ❌ [Issue]: [Reason for declining]

Commit: [commit hash]"
```

### Step 7: Commit Changes

```bash
git add -A
git commit -m "fix: address code review feedback

- [Change 1]
- [Change 2]
```

## Evaluation Criteria Details

### When to ACCEPT

- **Documentation issues**: Typos, inconsistencies, clarity improvements
- **Build optimization**: Cache improvements, layer ordering
- **Security issues** (in production code): Input validation, secret handling
- **Code quality**: Dead code removal, unused imports

### When to REJECT

- **Development environment over-engineering**: Excessive validation, complex health checks
- **Impractical suggestions**: Requires external dependencies, major refactoring
- **Security theater**: Suggestions that add complexity without real security benefit
- **Premature optimization**: Performance improvements without evidence of bottleneck

## Example Reply Templates

### For Rejected Security Suggestions (Dev Environment)

```
Thank you for the security consideration. This Dockerfile is for development environments only, not production deployment.

The suggested change would add complexity without meaningful security benefit in this context:
- [Specific reason 1]
- [Specific reason 2]

Resolving this conversation.
```

### For Rejected Over-Engineering

```
Thank you for the suggestion. While thorough validation is valuable, this level of checking introduces unnecessary complexity for a development container.

Our philosophy prioritizes simplicity over exhaustive verification in non-production contexts.

Resolving this conversation.
```

## Important Notes

- Always explain your reasoning when rejecting suggestions
- Be respectful in replies - AI reviewers provide valuable perspectives
- Prioritize fixes that improve code quality without adding complexity
- Run quality checks before committing
- Check AGENTS.md for project-specific commit message format
