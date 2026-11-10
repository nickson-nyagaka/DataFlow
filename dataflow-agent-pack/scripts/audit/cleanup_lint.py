#!/usr/bin/env python3
"""Run minor cleanups on audit scripts so ruff check is 100% clean."""

from pathlib import Path

AUDIT_DIR = Path(__file__).resolve().parent

# Fix verify_phase0_compliance.py
vpc_path = AUDIT_DIR / "verify_phase0_compliance.py"
content = vpc_path.read_text(encoding="utf-8")
content = content.replace("        meta = json.load(f)", "        json.load(f)")
vpc_path.write_text(content, encoding="utf-8")

# Fix parse_ast_columns.py
pac_path = AUDIT_DIR / "parse_ast_columns.py"
content = pac_path.read_text(encoding="utf-8")
content = content.replace(
    "    except Exception:", "    except (SyntaxError, ValueError):"
)
content = content.replace(
    "        except Exception as e2:", "        except (SyntaxError, ValueError) as e2:"
)
content = content.replace(
    """        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "agg":""",
    """        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "agg":""",
)
content = content.replace(
    """                if isinstance(target, ast.Name) and target.id == "headers":
                    # Extract list of tuples
                    if isinstance(node.value, ast.List):""",
    """                if isinstance(target, ast.Name) and target.id == "headers" and isinstance(node.value, ast.List):""",
)
pac_path.write_text(content, encoding="utf-8")

# Fix inspect_cell61.py
ic61_path = AUDIT_DIR / "inspect_cell61.py"
content = ic61_path.read_text(encoding="utf-8")
content = content.replace(
    'c61 = [c for c in cells if c["index"] == 61][0]["source"]',
    'c61 = next(c for c in cells if c["index"] == 61)["source"]',
)
content = content.replace(
    'for sec in sections:\n    print(f"- {sec} ({len(sections[sec])} lines)")',
    'for sec, sec_lines in sections.items():\n    print(f"- {sec} ({len(sec_lines)} lines)")',
)
ic61_path.write_text(content, encoding="utf-8")

# Fix remaining single element slices
for fname in [
    "inspect_c61_end.py",
    "inspect_c61_hts.py",
    "inspect_c61_mid.py",
    "inspect_c66.py",
    "inspect_c80_headers.py",
    "inspect_c80_part2.py",
    "inspect_c80_part3.py",
    "inspect_c82_lines.py",
    "inspect_c82_nsp.py",
]:
    fpath = AUDIT_DIR / fname
    if fpath.exists():
        txt = fpath.read_text(encoding="utf-8")
        # replace [c for c in cells if c["index"] == N][0] with next(c for c in cells if c["index"] == N)
        import re

        txt = re.sub(
            r'\[c for c in cells if c\["index"\] == (\d+)\]\[0\]',
            r'next(c for c in cells if c["index"] == \1)',
            txt,
        )
        fpath.write_text(txt, encoding="utf-8")

print("Cleaned up audit scripts.")
