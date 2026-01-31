#!/usr/bin/env python3
"""
Convert a Quarto blog notebook to a standalone Binder-ready notebook.

Usage:
    python scripts/convert_to_binder.py posts/word-counts/index.ipynb notebooks/word-counts.ipynb

This script:
1. Reads the Quarto blog notebook
2. Extracts metadata from the YAML frontmatter
3. Replaces the frontmatter cell with a markdown header
4. Removes blog-specific elements (Binder badge, preview image)
5. Writes a standalone notebook suitable for Binder
"""

import json
import re
import sys
from pathlib import Path


def extract_yaml_frontmatter(source: str) -> dict:
    """Extract metadata from Quarto YAML frontmatter."""
    # Match content between --- markers
    match = re.search(r'^---\s*\n(.*?)\n---\s*$', source, re.DOTALL)
    if not match:
        return {}

    yaml_content = match.group(1)
    metadata = {}

    # Simple YAML parsing for common fields
    for line in yaml_content.split('\n'):
        if ':' in line and not line.startswith(' '):
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value:
                metadata[key] = value

    return metadata


def create_binder_header(metadata: dict, blog_url: str) -> str:
    """Create a markdown header cell for the Binder notebook."""
    title = metadata.get('title', 'Untitled')
    description = metadata.get('description', '')
    author = metadata.get('author', 'Anonymous')
    date = metadata.get('date', '')

    # Format date for display (convert YYYY-MM-DD to MM.DD.YYYY)
    if date and '-' in date:
        parts = date.split('-')
        if len(parts) == 3:
            date = f"{parts[1]}.{parts[2]}.{parts[0]}"

    header = f"# {title}\n\n"
    if description:
        header += f"*{description} See full blog post [here]({blog_url}).*  \n"
    else:
        header += f"*See full blog post [here]({blog_url}).*  \n"
    header += "  \n"
    header += f"[{author}](https://diyclassics.github.io/)  \n"
    header += f"{date}"

    return header


def clean_markdown_cell(source: str) -> str:
    """Remove blog-specific elements from markdown cells."""
    lines = source.split('\n')
    cleaned_lines = []
    skip_until_empty = False

    for line in lines:
        # Skip Binder badge lines
        if 'mybinder.org' in line or 'Binder]' in line:
            skip_until_empty = True
            continue

        # Skip preview image spans
        if 'preview-image' in line or "src='preview.png'" in line:
            continue

        # Skip "Run this notebook" lines
        if 'Run this notebook in the browser' in line:
            skip_until_empty = True
            continue

        if skip_until_empty:
            if line.strip() == '':
                skip_until_empty = False
            continue

        cleaned_lines.append(line)

    # Remove leading/trailing empty lines
    while cleaned_lines and cleaned_lines[0].strip() == '':
        cleaned_lines.pop(0)
    while cleaned_lines and cleaned_lines[-1].strip() == '':
        cleaned_lines.pop()

    return '\n'.join(cleaned_lines)


def convert_notebook(input_path: Path, output_path: Path, blog_base_url: str = "https://diyclassics.github.io/epblog") -> None:
    """Convert a Quarto blog notebook to a Binder-ready notebook."""

    # Read the input notebook
    with open(input_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)

    # Determine blog post URL from path
    # e.g., posts/word-counts/index.ipynb -> posts/word-counts/
    post_slug = input_path.parent.name
    blog_url = f"{blog_base_url}/posts/{post_slug}/"

    new_cells = []
    metadata = {}
    first_cell = True

    for cell in notebook['cells']:
        cell_type = cell.get('cell_type', '')
        source = ''.join(cell.get('source', []))

        if first_cell:
            first_cell = False

            # Check if this is a raw cell with YAML frontmatter
            if cell_type == 'raw' and source.strip().startswith('---'):
                metadata = extract_yaml_frontmatter(source)

                # Create new markdown header cell
                header_source = create_binder_header(metadata, blog_url)
                new_cells.append({
                    'cell_type': 'markdown',
                    'metadata': {},
                    'source': header_source.split('\n')
                })
                continue

        # Clean markdown cells
        if cell_type == 'markdown':
            cleaned_source = clean_markdown_cell(source)
            if cleaned_source.strip():  # Only add non-empty cells
                new_cell = cell.copy()
                new_cell['source'] = cleaned_source.split('\n')
                # Ensure source lines have newlines except the last
                new_cell['source'] = [line + '\n' for line in new_cell['source'][:-1]] + [new_cell['source'][-1]]
                new_cells.append(new_cell)
        else:
            # Keep code cells as-is (but clear outputs)
            new_cell = cell.copy()
            if 'outputs' in new_cell:
                new_cell['outputs'] = []
            if 'execution_count' in new_cell:
                new_cell['execution_count'] = None
            new_cells.append(new_cell)

    # Create output notebook
    output_notebook = {
        'cells': new_cells,
        'metadata': notebook.get('metadata', {}),
        'nbformat': notebook.get('nbformat', 4),
        'nbformat_minor': notebook.get('nbformat_minor', 5)
    }

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write output notebook
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_notebook, f, indent=1, ensure_ascii=False)
        f.write('\n')

    print(f"Converted: {input_path} -> {output_path}")
    print(f"  Title: {metadata.get('title', 'Unknown')}")
    print(f"  Blog URL: {blog_url}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    convert_notebook(input_path, output_path)


if __name__ == '__main__':
    main()
