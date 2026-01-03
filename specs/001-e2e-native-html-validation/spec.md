# Feature Specification: E2Eテスト - ネイティブHTML変換検証

**Feature Branch**: `001-e2e-native-html-validation`
**Created**: 2026-01-01
**Status**: Draft
**Input**: User description: "GitHub Issue #47 コメント #issuecomment-3703264325 の指摘を解決するE2Eテスト仕様 - 現在のテストが自己生成HTMLを自己検証するトートロジーであるため、ブラウザ自動化でnote.comエディタを直接操作し、プラットフォームのネイティブHTML生成結果を検証する"

## Clarifications

### Session 2026-01-01

- Q: プレビューページでのHTML取得対象は何ですか？ → A: プレビューページのDOM（記事本文部分）を取得
- Q: テスト対象のMCPツール範囲は？ → A: note-mcpの実装済みツールすべて（ただしnote_publish_articleは絶対に除外）

### Session 2026-01-01 (Clarification #2)

- **問題**: User Stories 1-4はネイティブHTML検証のみをカバーしていたが、FR-001〜FR-006はMCPツールテストを要求していた。このミスマッチにより、MCPツールテストが実装されていなかった。
- **解決**: User Stories 5-8を追加し、MCPツールテスト要件（FR-001〜FR-006）をカバー
  - User Story 5: 認証フロー（login, check_auth, logout, set_username）
  - User Story 6: 記事CRUD操作（create_draft, get_article, update_article, list_articles）
  - User Story 7: 画像操作（upload_eyecatch, upload_body_image, insert_body_image）
  - User Story 8: プレビュー機能（show_preview）

### Session 2026-01-02

- Q: テスト対象に追加すべき編集機能の範囲は？ → A: 全記法（TOC、引用、リスト、番号付きリスト、リンク、太字、水平線）
- Q: 目次（TOC）の検証方法は？ → A: プレビューページでTOC要素（TableOfContentsクラス）を検証
- Q: 目次（TOC）のエディタへの入力方法は？ → A: `[TOC]`プレースホルダー入力後、`note_create_draft`または`note_update_article`経由でTOC挿入
- Q: 新規追加した編集機能のテスト優先度は？ → A: 全機能P1（同時に実装）
- Q: 各Markdown記法の期待HTMLは仕様で定義すべきか？ → A: 別の仕様で定義
- Q: リンクのProseMirrorトリガーパターンは？ → A: `[text](url)` + スペースでリンクに変換
- Q: 太字のProseMirrorトリガーパターンは？ → A: `**text**` + スペースで変換
- Q: 水平線のProseMirrorトリガーパターンは？ → A: `---` + Enterで水平線に変換
- Q: 引用・リストのProseMirrorトリガーパターンは？ → A: 行頭で `> ` / `- ` / `1. ` を入力するとブロックモードに変換
- Q: テスト失敗時のリトライ戦略は？ → A: 自動リトライ（最大3回、指数バックオフ）

## Test Scope - MCPツール対象範囲

### テスト対象ツール（12ツール）

| ツール名 | 機能 | テスト優先度 |
|----------|------|--------------|
| note_login | ログイン | P1 |
| note_check_auth | 認証状態確認 | P1 |
| note_logout | ログアウト | P2 |
| note_set_username | ユーザー名設定 | P2 |
| note_create_draft | 下書き作成 | P1 |
| note_get_article | 記事取得 | P1 |
| note_update_article | 記事更新 | P1 |
| note_upload_eyecatch | アイキャッチ画像アップロード | P2 |
| note_upload_body_image | 本文画像アップロード | P2 |
| note_insert_body_image | 本文画像挿入 | P2 |
| note_show_preview | プレビュー表示 | P1 |
| note_list_articles | 記事一覧取得 | P1 |

### テスト対象外ツール（厳禁）

| ツール名 | 理由 |
|----------|------|
| note_publish_article | **公開機能は絶対にテストしない** - 意図しない記事公開を防止 |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - ネイティブHTML変換検証テストの実行 (Priority: P1)

開発者として、Markdown記法をnote.comエディタに直接入力し、note.comプラットフォームが生成するネイティブHTMLを検証したい。これにより、自己生成HTMLの自己検証という「トートロジー」を排除し、実際のプラットフォーム動作との整合性を保証できる。

**Why this priority**: 現在のE2Eテストの根本的な欠陥（トートロジー）を解決する最も重要な機能。ユーザーが実際に体験するHTML出力を検証することで、テストの信頼性が大幅に向上する。

**Independent Test**: note.comの認証済みセッションでエディタを開き、Markdown記法を直接入力し、プレビューページで生成されたHTMLを取得・検証することで、単独でテスト可能。

**Acceptance Scenarios**:

1. **Given** 認証済みのnote.comセッション, **When** エディタで `## 見出し2` と入力しプレビューページを開く, **Then** プレビューページのDOMから `<h2>見出し2</h2>` を取得できる
2. **Given** 認証済みのnote.comセッション, **When** エディタで `~~打消し線~~` と入力しプレビューページを開く, **Then** プレビューページのDOMから `<s>打消し線</s>` を取得できる
3. **Given** 認証済みのnote.comセッション, **When** 複数のMarkdown記法を連続入力しプレビューページを開く, **Then** プレビューページのDOMから各記法に対応するネイティブHTMLを個別に検証できる

---

### User Story 2 - ProseMirrorトリガーパターンの適用 (Priority: P1)

開発者として、note.comのProseMirrorエディタが認識するMarkdownトリガーパターン（入力後のスペースなど）を正しく適用してテストを実行したい。これにより、Markdown記法が確実にHTMLに変換される。

**Why this priority**: note.comのエディタはProseMirrorベースであり、特定のトリガーパターン（パターン入力後のスペース）がないとMarkdown変換が発動しない。この知識なしではテストが失敗する。

**Independent Test**: 単一のMarkdown記法（例: `~~text~~`）を入力し、スペースをトリガーとして変換が発動することを確認できる。

**Acceptance Scenarios**:

1. **Given** エディタにフォーカスがある状態, **When** `~~テキスト~~` を入力後にスペースを押す, **Then** `<s>テキスト</s>` に変換される
2. **Given** エディタにフォーカスがある状態, **When** `~~テキスト~~` を入力後にEnterを押す, **Then** 変換は発動しない（プレーンテキストのまま）
3. **Given** 変換完了後, **When** 次の入力のためにバックスペースで不要なスペースを削除する, **Then** 変換結果は維持される

---

### User Story 3 - テスト結果の信頼性向上 (Priority: P2)

品質保証担当者として、テスト結果が「実際のユーザー体験」を反映していることを確認したい。テストがプラットフォームのネイティブ動作を検証することで、リリース判断の信頼性が向上する。

**Why this priority**: ビジネス価値の観点から、テスト結果がユーザー体験と乖離していると品質保証の意味がない。P1の機能が動作することを前提とした検証。

**Independent Test**: テスト実行後のレポートで「ネイティブHTML検証」と「自己生成HTML検証」の違いが明確に識別できることを確認。

**Acceptance Scenarios**:

1. **Given** ネイティブHTML検証テストが実行された, **When** テスト結果を確認する, **Then** 検証したHTMLがnote.comプラットフォーム生成であることが明示される
2. **Given** テストが失敗した, **When** エラーレポートを確認する, **Then** 期待されるネイティブHTMLと実際の出力の差分が明確に表示される

---

### User Story 4 - 複数のMarkdown記法の網羅的テスト (Priority: P3)

開発者として、サポートするすべてのMarkdown記法（見出し、打消し線、コードブロック、テキスト配置等）のネイティブHTML変換を網羅的にテストしたい。

**Why this priority**: 基本的な検証機能（P1、P2）が動作してから、カバレッジを拡大する。

**Independent Test**: 各Markdown記法ごとに独立したテストケースを実行できる。

**Acceptance Scenarios**:

1. **Given** テスト対象のMarkdown記法リスト, **When** 各記法に対してネイティブHTML検証を実行する, **Then** すべての記法が正しいHTMLに変換されることを確認できる
2. **Given** 新しいMarkdown記法がサポートされた, **When** テストケースを追加する, **Then** 既存のテスト基盤で新規記法も検証できる

---

### User Story 5 - MCPツール認証フローの検証 (Priority: P1)

開発者として、MCPツールの認証関連機能（login, check_auth, logout, set_username）が正しく動作することを検証したい。これにより、ユーザーがnote.comにアクセスする際の認証フローが確実に機能することを保証できる。

**Why this priority**: 認証はすべてのMCPツール操作の前提条件。認証が機能しなければ他のすべてのテストが失敗する。

**Independent Test**: 各認証ツールを単独で呼び出し、期待される結果（成功/失敗）を確認できる。

**Acceptance Scenarios**:

1. **Given** 未認証状態, **When** note_loginを呼び出す, **Then** ブラウザが開き手動ログイン後にセッションが保存される
2. **Given** 認証済み状態, **When** note_check_authを呼び出す, **Then** 認証状態が「有効」と返される
3. **Given** 認証済み状態, **When** note_logoutを呼び出す, **Then** セッションが削除され未認証状態になる
4. **Given** 認証済み状態, **When** note_set_usernameを呼び出す, **Then** ユーザー名が設定される

---

### User Story 6 - 記事CRUD操作の検証 (Priority: P1)

開発者として、MCPツールの記事操作機能（create_draft, get_article, update_article, list_articles）が正しく動作することを検証したい。これにより、記事の作成・取得・更新・一覧取得が確実に機能することを保証できる。

**Why this priority**: 記事操作はnote-mcpの中核機能。ユーザーが最も頻繁に使用する機能群。

**Independent Test**: 各記事操作ツールを単独で呼び出し、期待される結果を確認できる。

**Acceptance Scenarios**:

1. **Given** 認証済み状態, **When** note_create_draftを呼び出す, **Then** 下書き記事が作成され記事IDが返される
2. **Given** 作成済みの下書き記事, **When** note_get_articleを記事キーで呼び出す, **Then** 記事の内容（タイトル、本文、ステータス）が返される
3. **Given** 作成済みの下書き記事, **When** note_update_articleで内容を更新する, **Then** 記事の内容が更新される
4. **Given** 認証済み状態, **When** note_list_articlesを呼び出す, **Then** 自分の記事一覧が返される

---

### User Story 7 - 画像操作の検証 (Priority: P2)

開発者として、MCPツールの画像操作機能（upload_eyecatch, upload_body_image, insert_body_image）が正しく動作することを検証したい。これにより、記事への画像追加が確実に機能することを保証できる。

**Why this priority**: 画像操作は記事作成の重要な補助機能だが、テキスト操作より優先度は低い。

**Independent Test**: 各画像操作ツールを単独で呼び出し、画像がアップロード・挿入されることを確認できる。

**Acceptance Scenarios**:

1. **Given** 作成済みの下書き記事と画像ファイル, **When** note_upload_eyecatchを呼び出す, **Then** アイキャッチ画像が設定される
2. **Given** 作成済みの下書き記事と画像ファイル, **When** note_upload_body_imageを呼び出す, **Then** 本文用画像がアップロードされURLが返される
3. **Given** 作成済みの下書き記事と画像ファイル, **When** note_insert_body_imageを呼び出す, **Then** 本文に画像が挿入される

---

### User Story 8 - プレビュー機能の検証 (Priority: P1)

開発者として、MCPツールのプレビュー機能（show_preview）が正しく動作することを検証したい。これにより、ユーザーが記事を公開前に確認できることを保証できる。

**Why this priority**: プレビューは公開前の最終確認に必須の機能。

**Independent Test**: プレビューツールを単独で呼び出し、プレビューページが開くことを確認できる。

**Acceptance Scenarios**:

1. **Given** 作成済みの下書き記事, **When** note_show_previewを記事キーで呼び出す, **Then** プレビューページがブラウザで開く

---

### Edge Cases

- 認証セッションが切れた場合、テストは適切なエラーメッセージと共に失敗する
- エディタの読み込みが遅延した場合、適切なタイムアウト処理が行われる
- ネットワークエラーが発生した場合、自動リトライ（最大3回、指数バックオフ）が適用される
- 複雑なMarkdown記法（ネストされた記法など）で予期しない変換結果が生じた場合、差分が明確に報告される
- MCPツール呼び出しが失敗した場合、エラー内容が明確に報告される
- 画像ファイルが存在しない、またはフォーマットが不正な場合、適切なエラーが返される

## Requirements *(mandatory)*

### Functional Requirements

#### MCPツールテスト要件

- **FR-001**: テストはnote-mcpの12個のMCPツールすべてを検証対象としなければならない
- **FR-002**: テストはnote_publish_article（公開機能）を**絶対に呼び出してはならない**
- **FR-003**: テストは認証フロー（login, check_auth, logout, set_username）を検証できなければならない
- **FR-004**: テストは記事CRUD操作（create_draft, get_article, update_article, list_articles）を検証できなければならない
- **FR-005**: テストは画像操作（upload_eyecatch, upload_body_image, insert_body_image）を検証できなければならない
- **FR-006**: テストはプレビュー機能（show_preview）を検証できなければならない

#### ネイティブHTML変換検証要件

- **FR-007**: テストはブラウザ自動化を使用してnote.comエディタを直接操作できなければならない
- **FR-008**: テストはnote.comプレビューページのDOM（記事本文部分）からネイティブHTMLを取得できなければならない
- **FR-009**: テストはProseMirrorのトリガーパターン（スペースによるMarkdown変換発動）を正しく適用できなければならない
- **FR-010**: テストは自己生成HTMLではなく、プラットフォーム生成HTMLを検証対象としなければならない
- **FR-011**: テストは以下のすべてのMarkdown記法をサポートしなければならない（全てP1優先度）：
  - H2/H3見出し
  - 打消し線
  - コードブロック
  - テキスト配置
  - 目次（TOC）- `[TOC]`プレースホルダー＋`note_create_draft`/`note_update_article`経由で挿入、プレビューページのTableOfContentsクラスで検証
  - 引用（blockquote） - 行頭で `> ` を入力してブロックモードに変換
  - リスト（箇条書き） - 行頭で `- ` を入力してブロックモードに変換
  - 番号付きリスト - 行頭で `1. ` を入力してブロックモードに変換
  - リンク - `[text](url)` + スペースで変換（※ProseMirror InputRule未実装のためUI経由で挿入）
  - 太字（bold） - `**text**` + スペースで変換
  - 水平線 - `---` + Enterで変換

  **注**: 斜体（`*text*`）とインラインコード（`` `code` ``）はnote.comのProseMirrorスキーマに対応するマークがないためサポートされません（PR #88）。

  **注**: 各記法の期待HTMLマッピングは本仕様のdata-model.md（`MarkdownTestCase`定義）および将来の「Markdown-HTML変換仕様」で定義する

#### 安全性要件

- **FR-012**: テストは下書き記事のみを使用し、公開記事には影響を与えてはならない
- **FR-013**: テスト結果は期待されるHTMLと実際の出力の差分を明確に表示しなければならない

### Key Entities

- **TestCase**: 検証対象のMarkdown記法、期待されるネイティブHTML、テスト実行結果を含むテストケース
- **NativeHTMLResult**: note.comエディタから取得したネイティブHTML変換結果
- **ProseMirrorTrigger**: Markdown変換を発動させるトリガーパターン（スペース、Enter等）の定義

## Success Criteria *(mandatory)*

### Measurable Outcomes

#### MCPツールカバレッジ

- **SC-001**: 12個のMCPツールすべてに対するE2Eテストが存在する（カバレッジ100%）
- **SC-002**: note_publish_articleがテストコード内で一切呼び出されていないことが静的解析で確認できる

#### ネイティブHTML検証

- **SC-003**: すべてのテストケースでnote.comプラットフォーム生成のネイティブHTMLを取得できる（成功率100%）
- **SC-004**: テスト実行時間が1記法あたり10秒以内で完了する
- **SC-005**: FR-011で定義された11種類すべてのMarkdown記法が検証可能
- **SC-006**: テスト失敗時、期待値と実際の出力の差分が明確に識別できる
- **SC-007**: テストが「トートロジー」ではないことが、テストアーキテクチャのレビューで確認できる

## Assumptions

- note.comの認証済みセッション（Playwright session storage）が利用可能
- note.comのエディタはProseMirrorベースであり、Markdownトリガーパターンが既知（スペースで変換発動）
- 既存のnote-mcp基盤（Playwright統合）が再利用可能
- テストは下書き記事を使用し、公開記事には影響しない
