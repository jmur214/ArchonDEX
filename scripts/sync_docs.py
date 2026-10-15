import ast
import os
from pathlib import Path

def parse_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=str(filepath))
        except Exception as e:
            return f"Error parsing: {e}"
            
    docs = []
    
    module_doc = ast.get_docstring(tree)
    if module_doc:
        docs.append(f"**Module Docstring:** {module_doc.split(chr(10))[0]}")
    
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    for c in classes:
        doc = ast.get_docstring(c)
        doc_str = doc.split(chr(10))[0] if doc else "No docstring"
        docs.append(f"- **Class `{c.name}`**: {doc_str}")
        # Methods
        methods = [n for n in c.body if isinstance(n, ast.FunctionDef)]
        for m in methods:
            if m.name.startswith('_') and m.name != '__init__': continue
            mdoc = ast.get_docstring(m)
            mdoc_str = mdoc.split(chr(10))[0] if mdoc else ""
            if mdoc_str:
                docs.append(f"  - `def {m.name}()`: {mdoc_str}")
            else:
                 docs.append(f"  - `def {m.name}()`")
                 
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    for f in functions:
        if f.name.startswith('_'): continue
        doc = ast.get_docstring(f)
        doc_str = doc.split(chr(10))[0] if doc else "No docstring"
        docs.append(f"- **Function `{f.name}()`**: {doc_str}")
        
    if not docs:
        return "*No public classes or functions found.*"
    return "\n".join(docs)

def render_index(dir_path):
    """The index.md content `sync_directory` WOULD write for `dir_path`: the hand-written top half
    kept, the auto-generated code reference rebuilt from the directory's *.py docstrings. Returns
    (index_path, content), or None for a directory without a qualitative index. Pure: never writes."""
    p = Path(dir_path)
    if not p.exists() or not p.is_dir():
        return None
    index_file = p / "index.md"
    if not index_file.exists():
        # Only sync dirs that have qualitative indexes
        return None
    # Find active py files (ignore subdirectories for this shallow index)
    py_files = list(p.glob("*.py"))
    with open(index_file, 'r', encoding='utf-8') as f:
        content = f.read()
    marker = "<!-- AUTO-GENERATED: DO NOT EDIT BELOW -->"
    if marker in content:
        top_half = content.split(marker)[0]
    else:
        top_half = content + "\n\n"
    bottom_half = [marker]
    bottom_half.append("\n## Auto-Generated Code Reference\n")
    bottom_half.append("*This section is automatically built by `scripts/sync_docs.py`. Do not edit manually.*\n")
    for py in sorted(py_files):
        if py.name == "__init__.py": continue
        bottom_half.append(f"### `{py.name}`")
        parsed = parse_file(py)
        bottom_half.append(parsed)
        bottom_half.append("")
    return index_file, top_half + "\n".join(bottom_half)


def sync_directory(dir_path):
    rendered = render_index(dir_path)
    if rendered is None:
        return
    index_file, content = rendered
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Synced {index_file}")


def drifted(dirs=None) -> list:
    """The index files whose committed content differs from what a sync would write — the drift a
    docstring change leaves behind when nobody ran this script. Read-only."""
    out = []
    for d in (DIRS_TO_SYNC if dirs is None else dirs):
        rendered = render_index(d)
        if rendered is None:
            continue
        index_file, content = rendered
        if index_file.read_text(encoding='utf-8') != content:
            out.append(str(index_file))
    return out


DIRS_TO_SYNC = [
    "engines/engine_a_alpha",
    "engines/engine_b_risk",
    "engines/engine_c_portfolio",
    "engines/engine_d_discovery",
    "engines/engine_e_regime",
    "engines/engine_f_governance",
    "engines/data_manager",
    "orchestration",
    "scripts"
]

if __name__ == "__main__":
    import sys
    if "--check" in sys.argv[1:]:
        # Read-only (the nightly janitor's index_drift check): list the drifted indexes, exit 1.
        stale = drifted()
        for f in stale:
            print(f"DRIFT {f}")
        print(f"index drift: {len(stale)} file(s)" if stale else "index drift: none")
        sys.exit(1 if stale else 0)
    for d in DIRS_TO_SYNC:
        sync_directory(d)
