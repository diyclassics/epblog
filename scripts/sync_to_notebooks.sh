#!/bin/bash
#
# Sync blog posts to the notebooks branch for Binder
#
# Usage:
#   ./scripts/sync_to_notebooks.sh                    # Sync all posts with include_notebook: true
#   ./scripts/sync_to_notebooks.sh <post-slug>        # Sync a specific post
#   ./scripts/sync_to_notebooks.sh --list             # List posts that would be synced
#
# This script:
# 1. Finds all posts with include_notebook: true (or a specific post)
# 2. Converts them to Binder-ready notebooks
# 3. Switches to the notebooks branch
# 4. Copies the converted notebooks
# 5. Prompts for commit

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CONVERT_SCRIPT="$SCRIPT_DIR/convert_to_binder.py"

# Store current branch
CURRENT_BRANCH=$(git branch --show-current)

list_posts() {
    echo "Posts with include_notebook: true:"
    for post_dir in "$REPO_ROOT"/posts/*/; do
        if [ -f "$post_dir/index.ipynb" ]; then
            slug=$(basename "$post_dir")
            if python "$CONVERT_SCRIPT" --check "$post_dir/index.ipynb" 2>/dev/null; then
                echo "  - $slug"
            fi
        fi
    done
}

convert_single_post() {
    local slug="$1"
    local input="$REPO_ROOT/posts/$slug/index.ipynb"
    local output="/tmp/binder-notebooks/$slug.ipynb"

    if [ ! -f "$input" ]; then
        echo "Error: Post not found: $slug"
        return 1
    fi

    mkdir -p /tmp/binder-notebooks
    python "$CONVERT_SCRIPT" "$input" "$output" --force
}

convert_all_posts() {
    mkdir -p /tmp/binder-notebooks
    local count=0

    for post_dir in "$REPO_ROOT"/posts/*/; do
        if [ -f "$post_dir/index.ipynb" ]; then
            slug=$(basename "$post_dir")
            input="$post_dir/index.ipynb"
            output="/tmp/binder-notebooks/$slug.ipynb"

            if python "$CONVERT_SCRIPT" "$input" "$output" 2>/dev/null; then
                ((count++)) || true
            fi
        fi
    done

    echo ""
    echo "Converted $count notebook(s)"
}

# Handle arguments
case "${1:-}" in
    --list)
        list_posts
        exit 0
        ;;
    --help|-h)
        head -15 "$0" | tail -13
        exit 0
        ;;
    "")
        echo "Converting all posts with include_notebook: true..."
        convert_all_posts
        ;;
    *)
        echo "Converting post: $1"
        convert_single_post "$1"
        ;;
esac

# Check if any notebooks were converted
if [ ! -d /tmp/binder-notebooks ] || [ -z "$(ls -A /tmp/binder-notebooks 2>/dev/null)" ]; then
    echo "No notebooks to sync."
    exit 0
fi

echo ""
echo "Notebooks ready in /tmp/binder-notebooks/:"
ls -la /tmp/binder-notebooks/

echo ""
read -p "Switch to notebooks branch and copy files? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted. Notebooks remain in /tmp/binder-notebooks/"
    exit 0
fi

# Stash any changes and switch to notebooks branch
git stash --include-untracked 2>/dev/null || true
git fetch origin notebooks 2>/dev/null || true
git checkout notebooks

# Copy notebooks
mkdir -p "$REPO_ROOT/notebooks"
cp /tmp/binder-notebooks/*.ipynb "$REPO_ROOT/notebooks/"

# Stage changes
git add notebooks/

echo ""
echo "Changes staged. Review with:"
echo "  git diff --cached"
echo ""
echo "Then commit with:"
echo "  git commit -m 'Sync notebooks from blog'"
echo ""
echo "To return to your previous branch:"
echo "  git checkout $CURRENT_BRANCH && git stash pop"

# Clean up
rm -rf /tmp/binder-notebooks
