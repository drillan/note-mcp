#!/bin/bash

# プロジェクト名をディレクトリ名から取得
PROJECT_NAME=$(basename "$PWD")

# 著者名をgit configから取得
AUTHOR_NAME=$(git config user.name)

uv init .
uv venv

curl -o .gitignore https://raw.githubusercontent.com/github/gitignore/master/Python.gitignore

uv add ruff mypy pytest --dev
uv add sphinx sphinx_rtd_theme myst-parser sphinxcontrib-mermaid --group docs
uv run sphinx-quickstart -q -p "$PROJECT_NAME" -a "$AUTHOR_NAME" ./docs
sed -i "s/html_theme = 'alabaster'/html_theme = 'sphinx_rtd_theme'/" docs/conf.py
sed -i "s/extensions = \[\]/extensions = ['myst_parser', 'sphinxcontrib.mermaid']/" docs/conf.py
cat >> docs/conf.py << 'EOF'

# MyST Parser settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "tasklist",
]
EOF
uvx --from "rst-to-myst[sphinx]" rst2myst convert docs/index.rst
rm docs/index.rst