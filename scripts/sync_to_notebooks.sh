#!/bin/bash
#
# Sync a blog post to the notebooks branch for Binder
#
# Usage:
#   ./scripts/sync_to_notebooks.sh <post-slug>
#
# Example:
#   ./scripts/sync_to_notebooks.sh word-counts
#
# This script:
# 1. Converts the blog notebook to Binder format
# 2. Switches to the notebooks branch
# 3. Copies the converted notebook
# 4. Commits and optionally pushes

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <post-slug>"
    echo "Example: $0 word-counts"
    exit 1
fi

POST_SLUG="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
INPUT_PATH="$REPO_ROOT/posts/$POST_SLUG/index.ipynb"
OUTPUT_PATH="$REPO_ROOT/notebooks/$POST_SLUG.ipynb"

if [ ! -f "$INPUT_PATH" ]; then
    echo "Error: Blog notebook not found: $INPUT_PATH"
    exit 1
fi

# Store current branch
CURRENT_BRANCH=$(git branch --show-current)

echo "Converting $INPUT_PATH to Binder format..."
python "$SCRIPT_DIR/convert_to_binder.py" "$INPUT_PATH" "/tmp/$POST_SLUG-binder.ipynb"

echo "Switching to notebooks branch..."
git stash --include-untracked || true
git checkout notebooks

echo "Copying converted notebook..."
mkdir -p "$REPO_ROOT/notebooks"
cp "/tmp/$POST_SLUG-binder.ipynb" "$OUTPUT_PATH"

echo "Staging changes..."
git add "$OUTPUT_PATH"

echo ""
echo "Changes staged. Review with 'git diff --cached' then commit with:"
echo "  git commit -m 'Update $POST_SLUG notebook for Binder'"
echo ""
echo "To return to your previous branch:"
echo "  git checkout $CURRENT_BRANCH && git stash pop"
