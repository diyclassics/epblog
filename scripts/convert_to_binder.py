#!/usr/bin/env python3
"""
Convert a Quarto blog notebook to a standalone Binder-ready notebook.

Usage:
    python scripts/convert_to_binder.py posts/word-counts/index.ipynb notebooks/word-counts.ipynb
    python scripts/convert_to_binder.py --check posts/word-counts/index.ipynb  # Check if include_notebook is true

This script:
1. Reads the Quarto blog notebook
2. Checks for include_notebook: true in YAML frontmatter (skips if false/missing)
3. Extracts metadata from the YAML frontmatter
4. Replaces the frontmatter cell with a markdown header
5. If texts: field is present, generates a setup cell to fetch only those texts
6. Removes blog-specific elements (Binder badge, preview image, citations, references)
7. Writes a standalone notebook suitable for Binder
"""

import json
import re
import sys
from pathlib import Path


# Tesserae raw file URL template
TESSERAE_RAW_URL = "https://raw.githubusercontent.com/tesserae/tesserae/master/texts/la/{filename}"


def extract_yaml_frontmatter(source: str) -> dict:
    """Extract metadata from Quarto YAML frontmatter."""
    # Match content between --- markers
    match = re.search(r'^---\s*\n(.*?)\n---\s*$', source, re.DOTALL)
    if not match:
        return {}

    yaml_content = match.group(1)
    metadata = {}

    # Simple YAML parsing for common fields
    lines = yaml_content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        if ':' in line and not line.startswith(' ') and not line.startswith('-'):
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            # Check if this is a list (next lines start with '  -')
            if not value and i + 1 < len(lines) and lines[i + 1].strip().startswith('-'):
                # Parse YAML list
                items = []
                i += 1
                while i < len(lines) and lines[i].strip().startswith('-'):
                    item = lines[i].strip().lstrip('-').strip().strip('"').strip("'")
                    if item:
                        items.append(item)
                    i += 1
                metadata[key] = items
                continue
            elif value:
                # Check for inline list [item1, item2]
                if value.startswith('[') and value.endswith(']'):
                    items = [item.strip().strip('"').strip("'")
                             for item in value[1:-1].split(',')]
                    metadata[key] = [item for item in items if item]
                else:
                    metadata[key] = value
        i += 1

    return metadata


def should_include_notebook(metadata: dict) -> bool:
    """Check if the notebook should be converted (include_notebook: true)."""
    include = metadata.get('include_notebook', 'false')
    if isinstance(include, bool):
        return include
    return str(include).lower() == 'true'


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


def create_setup_cell(texts: list) -> str:
    """Create a setup code cell that fetches only the required texts."""
    if not texts:
        return None

    # Generate the list of files to fetch
    files_list = json.dumps(texts, indent=4)

    setup_code = f'''# Setup: Fetch required texts for this notebook
# This cell downloads only the specific texts needed, rather than the full corpus

import os
import urllib.request
from pathlib import Path

DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

TESSERAE_BASE_URL = "https://raw.githubusercontent.com/tesserae/tesserae/master/texts/la/"

REQUIRED_TEXTS = {files_list}

print("Fetching required texts...")
for filename in REQUIRED_TEXTS:
    local_path = DATA_DIR / filename
    if not local_path.exists():
        url = TESSERAE_BASE_URL + filename
        print(f"  Downloading {{filename}}...")
        try:
            urllib.request.urlretrieve(url, local_path)
        except Exception as e:
            print(f"  Warning: Could not fetch {{filename}}: {{e}}")
    else:
        print(f"  {{filename}} already exists")

print(f"Texts ready in {{DATA_DIR}}/")'''

    return setup_code


def create_setup_markdown() -> str:
    """Create markdown explaining the setup cell."""
    return """## Setup

First, let's fetch the texts needed for this notebook. This downloads only the specific files required, rather than the entire corpus."""


def generate_binder_link(post_slug: str, repo: str = "diyclassics/epblog", branch: str = "notebooks") -> str:
    """Generate the Binder badge markdown for a post."""
    notebook_path = f"notebooks/{post_slug}.ipynb"
    binder_url = f"https://mybinder.org/v2/gh/{repo}/{branch}?labpath={notebook_path.replace('/', '%2F')}"
    return f"[![Binder](https://mybinder.org/badge_logo.svg)]({binder_url})"


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

        # Skip Quarto reference sections
        if '::: {#refs}' in line or ':::' in line.strip():
            continue

        # Skip "References" header if it's alone
        if line.strip() == '### References':
            continue

        if skip_until_empty:
            if line.strip() == '':
                skip_until_empty = False
            continue

        cleaned_lines.append(line)

    # Remove Quarto citation syntax (@citation)
    cleaned_text = '\n'.join(cleaned_lines)
    cleaned_text = re.sub(r'\s*\(@\w+\)', '', cleaned_text)
    cleaned_text = re.sub(r'\(@\w+\)', '', cleaned_text)

    cleaned_lines = cleaned_text.split('\n')

    # Remove leading/trailing empty lines
    while cleaned_lines and cleaned_lines[0].strip() == '':
        cleaned_lines.pop(0)
    while cleaned_lines and cleaned_lines[-1].strip() == '':
        cleaned_lines.pop()

    return '\n'.join(cleaned_lines)


def transform_reader_init(source: str, has_texts: bool) -> str:
    """Transform reader initialization to use local data directory if texts are specified."""
    if not has_texts:
        return source

    # Replace TesseraeReader() with TesseraeReader("./data")
    # Handle various patterns
    patterns = [
        (r'TesseraeReader\(\)', 'TesseraeReader("./data")'),
        (r'TesseraeReader\(root=None\)', 'TesseraeReader("./data")'),
    ]

    result = source
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result)

    return result


def is_references_cell(source: str) -> bool:
    """Check if a cell is a Quarto references section."""
    return '### References' in source or '::: {#refs}' in source


def is_update_note_cell(source: str) -> bool:
    """Check if a cell is an update/publication note (blog-specific)."""
    return source.strip().startswith('---') and 'Originally published' in source


def convert_notebook(input_path: Path, output_path: Path, blog_base_url: str = "https://diyclassics.github.io/epblog", force: bool = False) -> bool:
    """Convert a Quarto blog notebook to a Binder-ready notebook.

    Returns True if conversion was performed, False if skipped.
    """

    # Read the input notebook
    with open(input_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)

    # Get first cell to check metadata
    first_cell = notebook['cells'][0] if notebook['cells'] else None
    metadata = {}

    if first_cell:
        cell_type = first_cell.get('cell_type', '')
        source = ''.join(first_cell.get('source', []))
        if cell_type == 'raw' and source.strip().startswith('---'):
            metadata = extract_yaml_frontmatter(source)

    # Check if we should convert this notebook
    if not force and not should_include_notebook(metadata):
        print(f"Skipped: {input_path} (include_notebook is not true)")
        return False

    # Get texts list if specified
    texts = metadata.get('texts', [])
    has_texts = bool(texts)

    # Determine blog post URL from path
    # e.g., posts/word-counts/index.ipynb -> posts/word-counts/
    post_slug = input_path.parent.name
    blog_url = f"{blog_base_url}/posts/{post_slug}/"

    new_cells = []
    first_cell_processed = False
    setup_cell_added = False

    for cell in notebook['cells']:
        cell_type = cell.get('cell_type', '')
        source = ''.join(cell.get('source', []))

        if not first_cell_processed:
            first_cell_processed = True

            # Check if this is a raw cell with YAML frontmatter
            if cell_type == 'raw' and source.strip().startswith('---'):
                # Create new markdown header cell
                header_source = create_binder_header(metadata, blog_url)
                new_cells.append({
                    'cell_type': 'markdown',
                    'metadata': {},
                    'source': header_source.split('\n')
                })

                # Add setup cells if texts are specified
                if has_texts:
                    # Add setup markdown
                    setup_md = create_setup_markdown()
                    new_cells.append({
                        'cell_type': 'markdown',
                        'metadata': {},
                        'source': setup_md.split('\n')
                    })

                    # Add setup code cell
                    setup_code = create_setup_cell(texts)
                    new_cells.append({
                        'cell_type': 'code',
                        'metadata': {},
                        'source': setup_code.split('\n'),
                        'outputs': [],
                        'execution_count': None
                    })
                    setup_cell_added = True

                continue

        # Skip references and update note cells
        if cell_type == 'markdown':
            if is_references_cell(source) or is_update_note_cell(source):
                continue

            cleaned_source = clean_markdown_cell(source)
            if cleaned_source.strip():  # Only add non-empty cells
                new_cell = cell.copy()
                new_cell['source'] = cleaned_source.split('\n')
                # Ensure source lines have newlines except the last
                new_cell['source'] = [line + '\n' for line in new_cell['source'][:-1]] + [new_cell['source'][-1]]
                new_cells.append(new_cell)
        else:
            # Code cell - transform reader init if needed
            new_cell = cell.copy()
            if has_texts:
                transformed_source = transform_reader_init(source, has_texts)
                new_cell['source'] = transformed_source.split('\n')
                # Ensure source lines have newlines except the last
                if new_cell['source']:
                    new_cell['source'] = [line + '\n' for line in new_cell['source'][:-1]] + [new_cell['source'][-1]]
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
    if has_texts:
        print(f"  Texts: {', '.join(texts)}")
    print(f"  Binder link: {generate_binder_link(post_slug)}")

    return True


def check_notebook(input_path: Path) -> bool:
    """Check if a notebook has include_notebook: true."""
    with open(input_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)

    first_cell = notebook['cells'][0] if notebook['cells'] else None

    if first_cell:
        cell_type = first_cell.get('cell_type', '')
        source = ''.join(first_cell.get('source', []))
        if cell_type == 'raw' and source.strip().startswith('---'):
            metadata = extract_yaml_frontmatter(source)
            return should_include_notebook(metadata)

    return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # Handle --check flag
    if sys.argv[1] == '--check':
        if len(sys.argv) < 3:
            print("Usage: convert_to_binder.py --check <input_notebook>")
            sys.exit(1)
        input_path = Path(sys.argv[2])
        if check_notebook(input_path):
            print(f"{input_path}: include_notebook=true")
            sys.exit(0)
        else:
            print(f"{input_path}: include_notebook=false (or not set)")
            sys.exit(1)

    # Handle --force flag
    force = '--force' in sys.argv
    args = [a for a in sys.argv[1:] if a != '--force']

    if len(args) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = Path(args[0])
    output_path = Path(args[1])

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    if convert_notebook(input_path, output_path, force=force):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
