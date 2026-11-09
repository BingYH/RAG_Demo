"""Record local reference revisions and selected source hashes; never fetch or pull."""

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SELECTION = {
    "docs": ["source/index.rst", "source/overview.rst", "source/troubleshooting.rst",
             "source/compatibility.rst", "source/_static/compatibility_data.py",
             "upstream.repos"],
    "libfranka": ["docs/overview.rst", "docs/system_requirements.rst",
                  "docs/getting_started.rst", "docs/compatibility_matrix.rst",
                  "docs/installation.rst"],
    "franka_ros2": ["README.md", "franka_bringup/doc/index.rst",
                    "franka_bringup/config/franka.config.yaml",
                    "franka_bringup/launch/franka.launch.py",
                    "franka_example_controllers/src/fr3/joint_impedance_example_controller.cpp"],
    "franka_description": ["README.rst"],
    "labs": ["README.md"],
    "libfranka-common": ["README.md", "CHANGELOG.md",
                         "include/research_interface/robot/service_types.h",
                         "include/research_interface/robot/rbk_types.h",
                         "include/research_interface/gripper/types.h"],
}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={repo.as_posix()}", "-C", str(repo), *args],
        text=True, encoding="utf-8", stderr=subprocess.PIPE,
    ).strip()


def main() -> None:
    repositories = []
    for name, paths in SELECTION.items():
        repo = ROOT / "references" / "repos" / name
        if not (repo / ".git").exists():
            raise SystemExit(f"Missing reference checkout: {name}")
        commit = git(repo, "rev-parse", "HEAD")
        files = []
        for relative in paths:
            path = repo / relative
            if not path.is_file():
                raise SystemExit(f"Missing source: {name}/{relative}")
            files.append({
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "upstream_url": f"https://github.com/frankarobotics/{name}/blob/{commit}/{relative}",
            })
        license_file = repo / "LICENSE"
        if not license_file.is_file():
            raise SystemExit(f"Missing LICENSE: {name}")
        repositories.append({
            "name": name,
            "repository": f"https://github.com/frankarobotics/{name}",
            "branch": git(repo, "branch", "--show-current") or "DETACHED",
            "commit": commit,
            "dirty": bool(git(repo, "status", "--porcelain", "--untracked-files=no")),
            "license_path": license_file.relative_to(ROOT).as_posix(),
            "license_sha256": hashlib.sha256(license_file.read_bytes()).hexdigest(),
            "files": files,
        })
    # Windows Python may lack the optional IANA timezone database.
    try:
        recorded = datetime.now(ZoneInfo("Europe/Berlin")).isoformat(timespec="seconds")
    except Exception:
        recorded = datetime.now().astimezone().isoformat(timespec="seconds")
    output = ROOT / "docs" / "source_manifest.json"
    output.write_text(json.dumps({"recorded_at": recorded,
                                  "repositories": repositories},
                                 ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded {len(repositories)} repositories, {sum(len(r['files']) for r in repositories)} files.")
    for repo in repositories:
        print(f"{repo['name']}: {repo['branch']} {repo['commit'][:12]} dirty={repo['dirty']}")


if __name__ == "__main__":
    main()
