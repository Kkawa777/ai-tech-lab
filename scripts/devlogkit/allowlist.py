"""Project allowlist (config/devlog-projects.yaml), deny-by-default.

Unchanged from Phase 1 except for being moved into this package. See
docs/devlog-policy.md section 6.1 for the full policy this implements.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "config" / "devlog-projects.yaml"


class AllowlistError(Exception):
    """Raised when a project fails allowlist validation. Callers decide
    whether that means exiting with an error or (for the daily runner)
    skipping just that one project."""


def load_allowlist():
    if not CONFIG_PATH.exists():
        raise AllowlistError(f"allowlist設定が見つかりません: {CONFIG_PATH}")
    with CONFIG_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("projects", {})


def resolve_and_validate_project(project_key, repo_arg, projects):
    if project_key not in projects:
        raise AllowlistError(
            f"project '{project_key}' は config/devlog-projects.yaml のallowlistに"
            "存在しません。deny-by-defaultのため処理しません。"
        )
    entry = projects[project_key]
    if not entry.get("enabled") or not entry.get("public"):
        raise AllowlistError(
            f"project '{project_key}' は enabled/public のいずれかが false のため"
            "対象外です(公開可否が確認できないrepositoryを勝手に処理しない設計)。"
        )
    configured_path = (ROOT / entry["path"]).resolve()
    actual_path = Path(repo_arg).resolve()
    if configured_path != actual_path:
        raise AllowlistError(
            "--repo の実パスが allowlist設定の path と一致しません。"
            "project名の詐称によるallowlistバイパスを防ぐため中断します。"
        )
    if not (actual_path / ".git").exists():
        raise AllowlistError(f"{actual_path} はGitリポジトリではありません(.gitが見つかりません)。")
    return entry, actual_path


def enabled_public_projects(projects):
    """Yield (key, entry, resolved_path) for every project that is both
    enabled and public, resolving its path relative to ROOT. Used by the
    daily runner to iterate without requiring an explicit --repo per call."""
    for key, entry in projects.items():
        if not entry.get("enabled") or not entry.get("public"):
            continue
        resolved = (ROOT / entry["path"]).resolve()
        if not (resolved / ".git").exists():
            continue
        yield key, entry, resolved
