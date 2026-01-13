# Tasks: 下書き記事の削除機能

**Input**: Design documents from `/specs/141-delete-draft/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD Required per Constitution Article 1 - all test tasks must be written and fail before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/note_mcp/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify existing infrastructure and prepare for implementation

- [X] T001 Verify existing NoteAPIClient.delete() method in src/note_mcp/api/client.py
- [X] T002 Verify existing ArticleStatus enum and Article model in src/note_mcp/models.py
- [X] T003 Verify existing list_articles and get_article functions in src/note_mcp/api/articles.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add data models and their tests required by all user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational Models (TDD Required per Article 1) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T004 [P] Unit test for ArticleSummary model in tests/unit/test_delete_models.py
- [X] T005 [P] Unit test for FailedArticle model in tests/unit/test_delete_models.py
- [X] T006 [P] Unit test for DeleteResult model in tests/unit/test_delete_models.py
- [X] T007 [P] Unit test for DeletePreview model in tests/unit/test_delete_models.py
- [X] T008 [P] Unit test for BulkDeletePreview model in tests/unit/test_delete_models.py
- [X] T009 [P] Unit test for BulkDeleteResult model in tests/unit/test_delete_models.py
- [X] T010 [P] Unit test for DeleteDraftInput model in tests/unit/test_delete_models.py
- [X] T011 [P] Unit test for DeleteAllDraftsInput model in tests/unit/test_delete_models.py

### Implementation for Foundational Models

- [X] T012 [P] Add ArticleSummary model in src/note_mcp/models.py
- [X] T013 [P] Add FailedArticle model in src/note_mcp/models.py
- [X] T014 [P] Add DeleteResult model in src/note_mcp/models.py
- [X] T015 [P] Add DeletePreview model in src/note_mcp/models.py
- [X] T016 [P] Add BulkDeletePreview model in src/note_mcp/models.py
- [X] T017 [P] Add BulkDeleteResult model in src/note_mcp/models.py
- [X] T018 [P] Add DeleteDraftInput model in src/note_mcp/models.py
- [X] T019 [P] Add DeleteAllDraftsInput model in src/note_mcp/models.py
- [X] T020 Add delete error message constants in src/note_mcp/models.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - 下書き記事の削除 (Priority: P1) 🎯 MVP

**Goal**: ユーザーが記事キーを指定して下書き記事を削除できる（確認フラグによる誤操作防止付き）

**Independent Test**: 下書き記事のキーを指定して削除ツールを呼び出し、削除成功のメッセージを受け取る。

### Tests for User Story 1 (TDD Required per Article 1) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T021 [P] [US1] Unit test for delete_draft function (confirm=False returns preview) in tests/unit/test_delete_draft.py
- [X] T022 [P] [US1] Unit test for delete_draft function (confirm=True executes deletion) in tests/unit/test_delete_draft.py
- [X] T023 [P] [US1] Unit test for delete_draft function (unauthenticated returns error) in tests/unit/test_delete_draft.py

### Implementation for User Story 1

- [X] T024 [US1] Implement delete_draft function in src/note_mcp/api/articles.py
  - Takes article_key and confirm flag
  - Returns DeleteResult on success or DeletePreview when confirm=False
  - Uses NoteAPIClient.delete() with path `/v1/notes/n/{article_key}`
- [X] T025 [US1] Add note_delete_draft MCP tool registration in src/note_mcp/server.py
  - Uses DeleteDraftInput for input validation
  - Returns DeleteResult, DeletePreview, or error response
- [X] T026 [US1] Export delete_draft from src/note_mcp/api/__init__.py
- [X] T027 [US1] Run code quality checks (ruff check, ruff format, mypy) for US1 changes

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - 公開済み記事の削除拒否 (Priority: P1)

**Goal**: 公開済み記事の削除を試みた場合に適切なエラーメッセージを返す

**Independent Test**: 公開済み記事のキーを指定して削除ツールを呼び出し、削除拒否のエラーメッセージを受け取る。

### Tests for User Story 2 (TDD Required per Article 1) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T028 [P] [US2] Unit test for delete_draft function (published article returns error) in tests/unit/test_delete_draft.py

### Implementation for User Story 2

- [X] T029 [US2] Add published article check to delete_draft function in src/note_mcp/api/articles.py
  - Fetch article with get_article() before deletion
  - Return error if status is PUBLISHED
  - Use DELETE_ERROR_PUBLISHED_ARTICLE message constant
- [X] T030 [US2] Run code quality checks (ruff check, ruff format, mypy) for US2 changes

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - すべての下書き記事の一括削除 (Priority: P2)

**Goal**: ユーザーがすべての下書き記事を一度に削除できる（2段階確認方式）

**Independent Test**: 一括削除ツールを呼び出し、削除対象件数を確認後、再度呼び出して全下書きが削除されることを確認。

### Tests for User Story 3 (TDD Required per Article 1) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T031 [P] [US3] Unit test for delete_all_drafts function (confirm=False returns preview) in tests/unit/test_delete_all_drafts.py
- [X] T032 [P] [US3] Unit test for delete_all_drafts function (confirm=True executes bulk deletion) in tests/unit/test_delete_all_drafts.py
- [X] T033 [P] [US3] Unit test for delete_all_drafts function (no drafts returns empty message) in tests/unit/test_delete_all_drafts.py
- [X] T034 [P] [US3] Unit test for delete_all_drafts function (partial failure returns detailed result) in tests/unit/test_delete_all_drafts.py

### Implementation for User Story 3

- [X] T035 [US3] Implement delete_all_drafts function in src/note_mcp/api/articles.py
  - Uses list_articles(status=DRAFT) to get all drafts
  - Returns BulkDeletePreview when confirm=False
  - Sequentially deletes each draft when confirm=True
  - Returns BulkDeleteResult with success/failure counts
- [X] T036 [US3] Add note_delete_all_drafts MCP tool registration in src/note_mcp/server.py
  - Uses DeleteAllDraftsInput for input validation
  - Returns BulkDeleteResult, BulkDeletePreview, or error response
- [X] T037 [US3] Export delete_all_drafts from src/note_mcp/api/__init__.py
- [X] T038 [US3] Run code quality checks (ruff check, ruff format, mypy) for US3 changes

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work independently

---

## Phase 6: User Story 4 - 存在しない記事・アクセス権のない記事の削除試行 (Priority: P2)

**Goal**: 存在しない記事キーや他ユーザーの記事キーを指定した場合に適切なエラーメッセージを返す

**Independent Test**: 存在しない記事キーを指定して削除ツールを呼び出し、エラーメッセージを受け取る。

### Tests for User Story 4 (TDD Required per Article 1) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T039 [P] [US4] Unit test for delete_draft function (article not found returns 404 error) in tests/unit/test_delete_draft.py
- [X] T040 [P] [US4] Unit test for delete_draft function (access denied returns 403 error) in tests/unit/test_delete_draft.py

### Implementation for User Story 4

- [X] T041 [US4] Add error handling for 404/403 responses in delete_draft function in src/note_mcp/api/articles.py
  - Handle ARTICLE_NOT_FOUND for 404
  - Handle API_ERROR with access denied message for 403
  - Use appropriate error message constants
- [X] T042 [US4] Run code quality checks (ruff check, ruff format, mypy) for US4 changes

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and quality assurance

- [X] T043 Run full code quality suite: uv run ruff check --fix . && uv run ruff format . && uv run mypy .
- [X] T044 Run all tests: uv run pytest tests/unit/test_delete_*.py -v
- [X] T045 Validate quickstart.md scenarios manually
- [X] T046 Verify all models exported correctly from src/note_mcp/models.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verification only
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
  - Tests (T004-T011) must FAIL before implementation (T012-T020)
- **User Story 1 (Phase 3)**: Depends on Foundational - core single delete
  - Tests (T021-T023) must FAIL before implementation (T024-T027)
- **User Story 2 (Phase 4)**: Depends on Phase 3 (adds check to delete_draft)
  - Test (T028) must FAIL before implementation (T029-T030)
- **User Story 3 (Phase 5)**: Can start after Foundational - independent bulk delete
  - Tests (T031-T034) must FAIL before implementation (T035-T038)
- **User Story 4 (Phase 6)**: Depends on Phase 3 (adds error handling to delete_draft)
  - Tests (T039-T040) must FAIL before implementation (T041-T042)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Core single delete - blocks US2 and US4
- **User Story 2 (P1)**: Adds published article check to US1's delete_draft
- **User Story 3 (P2)**: Independent - only depends on Foundational
- **User Story 4 (P2)**: Adds error handling to US1's delete_draft

### TDD Workflow per Phase

1. Write test(s) for the phase
2. Run tests - verify they FAIL (Red phase)
3. Implement the functionality
4. Run tests - verify they PASS (Green phase)
5. Run quality checks
6. Refactor if needed (maintaining passing tests)

### Parallel Opportunities

- All Foundational test tasks (T004-T011) marked [P] can run in parallel
- All Foundational implementation tasks (T012-T019) marked [P] can run in parallel
- User Story 3 can be implemented in parallel with User Stories 2 and 4
- Test tasks within each user story marked [P] can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Launch all model test tasks together (Red phase):
Task: "Unit test for ArticleSummary model in tests/unit/test_delete_models.py"
Task: "Unit test for FailedArticle model in tests/unit/test_delete_models.py"
Task: "Unit test for DeleteResult model in tests/unit/test_delete_models.py"
# ... etc

# Verify tests FAIL

# Launch all model implementation tasks together (Green phase):
Task: "Add ArticleSummary model in src/note_mcp/models.py"
Task: "Add FailedArticle model in src/note_mcp/models.py"
Task: "Add DeleteResult model in src/note_mcp/models.py"
# ... etc

# Verify tests PASS
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verification)
2. Complete Phase 2: Foundational (tests first, then models)
3. Complete Phase 3: User Story 1 (tests first, then implementation)
4. **STOP and VALIDATE**: Run all tests, verify US1 works independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (TDD) → Test single delete → MVP ready!
3. Add User Story 2 (TDD) → Test published article rejection
4. Add User Story 3 (TDD) → Test bulk delete independently
5. Add User Story 4 (TDD) → Test error handling
6. Each story adds value without breaking previous stories

### Single Developer Strategy

1. Complete Setup (T001-T003): ~5 min verification
2. Complete Foundational Tests (T004-T011): Write failing tests
3. Complete Foundational Implementation (T012-T020): Make tests pass
4. Complete User Story 1 Tests (T021-T023): Write failing tests
5. Complete User Story 1 Implementation (T024-T027): Make tests pass
6. Continue TDD pattern for remaining user stories...
7. Complete Polish (T043-T046): Final validation

---

## Test File Structure

```
tests/unit/
├── test_delete_models.py      # T004-T011: Pydanticモデルのテスト
├── test_delete_draft.py       # T021-T023, T028, T039-T040: 単体削除のテスト
└── test_delete_all_drafts.py  # T031-T034: 一括削除のテスト
```

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **TDD is mandatory**: Tests must be written and FAIL before implementation
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All models are added to existing src/note_mcp/models.py (no new files)
- All API functions are added to existing src/note_mcp/api/articles.py (no new files)
- MCP tools are registered in existing src/note_mcp/server.py (no new files)
