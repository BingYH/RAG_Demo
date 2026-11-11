"""Audit project-owned text; exclude vendor material and historical runtime data."""

import ast
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = "rag_demo/ui_i18n.py"
LOCALIZED_DOCUMENTS = {
    "docs/interview_demo/Chinese/README.md",
    "docs/interview_demo/Chinese/run_of_show.md",
    "docs/interview_demo/Chinese/speaker_notes.md",
}
EXCLUDED = ("references/", ".venv/", "venv/", "data/", "evaluation/results/")
CJK = re.compile(f"[{chr(0x3400)}-{chr(0x9fff)}]")


def audit_text(name: str, source: str) -> list[str]:
    """Check visible prose and escaped Python prose without rejecting range bounds."""
    if name == CATALOG or name in LOCALIZED_DOCUMENTS or name.startswith(EXCLUDED):
        return []
    issues = [f"{name}:{number}: Chinese text outside the UI catalog"
              for number, line in enumerate(source.splitlines(), 1) if CJK.search(line)]
    if name.endswith(".py"):
        for node in ast.walk(ast.parse(source, filename=name)):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if len(CJK.findall(node.value)) > 1 and not CJK.search(ast.get_source_segment(source, node) or ""):
                    issues.append(f"{name}:{node.lineno}: escaped Chinese prose outside the UI catalog")
    return issues


def main() -> int:
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, check=True, capture_output=True)
    names = sorted(set(result.stdout.decode("utf-8").split("\0")) - {""})
    issues, checked = [], 0
    for name in names:
        path = ROOT / name
        if name.startswith(EXCLUDED) or not path.is_file():
            continue
        try:
            source = path.read_text(encoding="utf-8-sig")
        except UnicodeError:
            continue  # Binary artifacts are outside this prose audit.
        checked += 1
        issues.extend(audit_text(name, source))
    for issue in issues:
        print(issue)
    print(f"LANGUAGE_AUDIT: {'FAIL' if issues else 'PASS'} ({checked} project files; UI catalog and approved Chinese translations allowed)")
    return int(bool(issues))


if __name__ == "__main__":
    raise SystemExit(main())
