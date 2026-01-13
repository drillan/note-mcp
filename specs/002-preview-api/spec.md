# Feature Specification: プレビューAPI対応

**Feature Branch**: `002-preview-api`
**Created**: 2025-01-13
**Status**: Draft
**Parent Spec**: `specs/001-note-mcp/spec.md`
**Input**: User description: "specs/001-note-mcp/spec.md を親仕様としたプレビュー機能の仕様として定義してください"

## Overview

note.com MCP Serverのプレビュー機能を拡張し、以下の2つの利用モードを提供する:

1. **人間確認用モード**: Playwrightブラウザでプレビューページを表示（視覚確認用）
2. **プログラム用モード**: API経由でプレビューHTMLを取得（E2Eテスト・AI検証用）

現在のプレビュー機能はエディターページ経由でブラウザ操作を行っており、遅く不安定。
API経由で`preview_access_token`を取得し、直接プレビューURLにアクセスすることで高速化・安定化を図る。

**技術的背景**:
- APIエンドポイント: `POST /api/v2/notes/{article_key}/access_tokens`
- レスポンス: `{"data": {"preview_access_token": "..."}}`
- プレビューURL: `https://note.com/preview/{article_key}?prev_access_key={token}`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - ブラウザでプレビュー表示（人間確認用） (Priority: P1)

ユーザーがAIアシスタントを通じて記事のプレビューを確認する。ブラウザでプレビューページが開き、視覚的に記事の見た目を確認できる。

**Why this priority**: 人間がプレビューを確認するのは最も基本的なユースケースであり、既存機能の改善版。

**Independent Test**: プレビューツールを呼び出し、ブラウザでプレビューページが表示され、記事内容が正しく見えることを確認。

**Acceptance Scenarios**:

1. **Given** ユーザーが認証済みで下書き記事がある, **When** `note_show_preview`を記事キーを指定して呼び出す, **Then** ブラウザでプレビューページが開き、記事内容が表示される
2. **Given** ユーザーが認証済み, **When** プレビューを表示する, **Then** エディターページを経由せず直接プレビューURLにアクセスするため、3秒以内に表示が完了する
3. **Given** 既にプレビュータブが開いている, **When** 別の記事のプレビューを表示する, **Then** 既存のタブが更新されるか新しいタブで開く

---

### User Story 2 - プレビューHTMLの取得（プログラム用） (Priority: P1)

E2Eテストやコンテンツ検証のために、プレビューページのHTMLを取得する。AIが記事内容を検証したり、テストコードがDOM構造を確認するために使用する。

**Why this priority**: E2Eテストの高速化と安定化に必須。現在のPlaywrightベーステストは遅く不安定。

**Independent Test**: HTML取得ツールを呼び出し、プレビューページのHTMLが文字列として返され、期待する要素（見出し、本文等）が含まれていることを確認。

**Acceptance Scenarios**:

1. **Given** ユーザーが認証済みで下書き記事がある, **When** `note_get_preview_html`を記事キーを指定して呼び出す, **Then** プレビューページのHTMLが文字列として返される
2. **Given** HTMLを取得した, **When** HTMLを解析する, **Then** 記事のタイトル、本文、見出し構造が正しく含まれている
3. **Given** 目次（TOC）を含む記事, **When** HTMLを取得する, **Then** 目次のHTML構造が含まれている
4. **Given** 数式を含む記事, **When** HTMLを取得する, **Then** KaTeXでレンダリングされた数式のHTML構造が含まれている
5. **Given** 画像を含む記事, **When** HTMLを取得する, **Then** note.com CDN上の画像URLを持つimg要素が含まれている

---

### User Story 3 - 認証エラー時の適切なハンドリング (Priority: P2)

未認証状態やセッション期限切れ時に、適切なエラーメッセージを返す。

**Why this priority**: エラーハンドリングは機能の信頼性を高める補助機能。

**Independent Test**: 未認証状態でプレビュー機能を呼び出し、ログインを促すエラーメッセージが返されることを確認。

**Acceptance Scenarios**:

1. **Given** ユーザーが未認証, **When** プレビュー機能を呼び出す, **Then** ログインが必要である旨のエラーメッセージが返される
2. **Given** セッションが期限切れ, **When** プレビュー機能を呼び出す, **Then** 再ログインを促すエラーメッセージが返される

---

### Edge Cases

- 存在しない記事キーを指定した場合はどうなるか？→ APIからエラーレスポンスを受け取り、適切なエラーメッセージを返す
- 他ユーザーの記事キーを指定した場合はどうなるか？→ アクセス権がないためエラーメッセージを返す
- 公開済み記事のプレビューを要求した場合はどうなるか？→ プレビューURLでアクセスを試み、成功すればプレビューを表示。APIがエラーを返す場合は公開URLを返す
- プレビュートークンの有効期限が切れた場合はどうなるか？→ APIで新しいトークンを取得して再試行

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: システムは`note_show_preview`ツールでブラウザにプレビューページを表示できなければならない
- **FR-002**: システムは`note_get_preview_html`ツールでプレビューページのHTMLを取得できなければならない
- **FR-003**: システムはAPI経由で`preview_access_token`を取得し、直接プレビューURLにアクセスしなければならない（エディター経由ではなく）
- **FR-004**: システムはプレビューURLとして`https://note.com/preview/{article_key}?prev_access_key={token}`形式を使用しなければならない
- **FR-005**: システムは未認証・セッション期限切れ時に適切なエラーメッセージを返さなければならない
- **FR-006**: システムは存在しない記事キーや権限のない記事に対して適切なエラーメッセージを返さなければならない

### Key Entities

- **PreviewAccessToken（プレビューアクセストークン）**: 下書き記事のプレビューにアクセスするための一時的なトークン。APIから取得される
- **PreviewURL（プレビューURL）**: プレビューページにアクセスするためのURL。記事キーとアクセストークンで構成される

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: プレビュー表示は呼び出しから3秒以内に完了する（現行のエディター経由方式より大幅に高速化）
- **SC-002**: E2Eテストのプレビュー検証は現行のPlaywright UIクリック方式と比較して80%以上高速化される
- **SC-003**: プレビューHTML取得は5秒以内に完了する
- **SC-004**: 取得したHTMLには記事の主要コンテンツ（タイトル、本文、見出し）が含まれている
- **SC-005**: エラー発生時、ユーザーは何が問題で何をすべきか理解できるメッセージを受け取る

## Assumptions

- 親仕様（001-note-mcp）で定義された認証機能が利用可能である
- `POST /api/v2/notes/{article_key}/access_tokens` APIは安定して動作する
- プレビューURLの形式（`?prev_access_key=`パラメータ）は維持される
- プレビューアクセストークンには有効期限があるが、通常の操作時間内（数分〜数十分）は有効である
