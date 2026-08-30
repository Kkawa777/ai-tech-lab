#!/usr/bin/env python3
"""Test suite for the Dev Log automation pipeline (Phase 2, Step 26).

Two kinds of tests:
  - Unit tests against synthetic data (no git needed) for the
    safety-critical logic: secret filtering, path denylist, allowlist
    validation, score gates/thresholds.
  - Integration tests against this actual repository's own real Git
    history (known dates from earlier in this project's development),
    exercising the full collect->sanitize->score->generate pipeline.

Run: python scripts/test_devlog.py
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from devlogkit import allowlist, classify, sanitize, score, security  # noqa: E402
from devlogkit import frontmatter as fm_lib  # noqa: E402
from devlogkit import pipeline  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_script_module(name):
    """scripts/run-daily-devlog.py etc. have hyphens, so they can't be
    imported with a normal `import` statement — load by file path instead.
    Used so tests exercise the REAL CLI module, not a reimplementation of
    its logic (a prior version of TestMultiProjectFailureIsolation copied
    the loop body inline here, which meant a regression in the actual
    script would never have been caught by this suite)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Unit tests: security / classify / score (no git, no filesystem side effects)
# ---------------------------------------------------------------------------

class TestSecretFiltering(unittest.TestCase):
    def test_secret_commit_message(self):
        self.assertTrue(security.contains_secret_pattern("remove hardcoded API key"))
        self.assertTrue(security.contains_secret_pattern("rotate access key"))
        self.assertFalse(security.contains_secret_pattern("add affiliate link"))

    def test_secret_filename(self):
        self.assertTrue(security.filename_is_secret_like(".env.production"))
        self.assertTrue(security.filename_is_secret_like("config/credentials.json"))
        self.assertFalse(security.filename_is_secret_like("_articles/esp32-rain-sensor-detection.md"))

    def test_path_denylist(self):
        self.assertTrue(security.is_denylisted_path(".env"))
        self.assertTrue(security.is_denylisted_path("id_rsa"))
        self.assertTrue(security.is_denylisted_path("node_modules/foo/index.js"))
        self.assertTrue(security.is_denylisted_path("package-lock.json"))
        self.assertFalse(security.is_denylisted_path("scripts/generate-devlog.py"))

    def test_secret_value_scan(self):
        self.assertTrue(security.scan_lines_for_secrets(["+AWS_KEY = 'AKIAABCDEFGHIJKLMNOP'"]))
        self.assertTrue(security.scan_lines_for_secrets(["+token = sk-abcdefghijklmnopqrstuvwx"]))
        self.assertFalse(security.scan_lines_for_secrets(["+def add(a, b):", "+    return a + b"]))


class TestTrivialClassification(unittest.TestCase):
    def test_trivial_prefixes(self):
        self.assertTrue(classify.is_trivial({"subject": "chore: bump deps"}, [{"status": "M", "path": "package-lock.json"}]))
        self.assertTrue(classify.is_trivial({"subject": "fix typo in README"}, [{"status": "M", "path": "README.md"}]))

    def test_substantive_commit_mentioning_typo_not_trivial(self):
        # Regression test: a commit that merely *mentions* "typo" mid
        # sentence must not be silently dropped (Phase 2 round-2 MAJOR fix).
        self.assertFalse(classify.is_trivial(
            {"subject": "fix: correct a typo and add rate limiting"},
            [{"status": "M", "path": "src/auth.py"}],
        ))

    def test_readme_only_is_trivial(self):
        self.assertTrue(classify.is_trivial(
            {"subject": "update installation section"},
            [{"status": "M", "path": "README.md"}],
        ))

    def test_mixed_files_not_trivial(self):
        self.assertFalse(classify.is_trivial(
            {"subject": "update installation section"},
            [{"status": "M", "path": "README.md"}, {"status": "M", "path": "src/main.py"}],
        ))


class TestQualityScoreGates(unittest.TestCase):
    def test_low_score_skip(self):
        day_stats = {"notable_commit_count": 1, "insertions": 2, "deletions": 0, "total_files_changed": 1}
        summary = {"functions_added": [], "classes_added": [], "tests_added": [], "docs_excerpts": [],
                   "evidence": [], "files_skipped_for_safety": [], "behavior_pairs": []}
        total, _ = score.compute_quality_score(day_stats, summary, classify.GENERIC, 0.0)
        gates = {"security": "PASS", "privacy": "PASS", "fact": "PASS", "reasons": []}
        self.assertEqual(score.decide(total, gates), score.SKIP)

    def test_high_score_auto_publish_candidate(self):
        day_stats = {"notable_commit_count": 3, "insertions": 300, "deletions": 50, "total_files_changed": 6}
        summary = {
            "functions_added": ["do_thing"], "classes_added": ["Thing"], "tests_added": ["test_do_thing"],
            "docs_excerpts": ["This does the thing."],
            "evidence": ["abc1234:src/thing.py (function signature added)"] * 5,
            "files_skipped_for_safety": [], "behavior_pairs": [("old", "new")],
        }
        total, _ = score.compute_quality_score(day_stats, summary, classify.FEATURE, 1.0)
        gates = {"security": "PASS", "privacy": "PASS", "fact": "PASS", "reasons": []}
        self.assertEqual(score.decide(total, gates), score.AUTO_PUBLISH_CANDIDATE)

    def test_security_gate_failure_forces_blocked_regardless_of_score(self):
        gates = {"security": "FAIL", "privacy": "PASS", "fact": "PASS", "reasons": ["security: ..."]}
        self.assertEqual(score.decide(100, gates), score.BLOCKED)

    def test_final_text_secret_rescan_catches_leak(self):
        rendered = "title: hello\nbody: AWS key AKIAABCDEFGHIJKLMNOP leaked\n"
        gates = score.check_safety_gates(rendered, {"evidence": [], "files_skipped_for_safety": []})
        self.assertEqual(gates["security"], "FAIL")

    def test_privacy_gate_catches_windows_path(self):
        rendered = "some text referencing C:\\Users\\jsmith\\secret-project\\notes.txt"
        gates = score.check_safety_gates(rendered, {"evidence": [], "files_skipped_for_safety": []})
        self.assertEqual(gates["privacy"], "FAIL")

    def test_fact_gate_contradiction_detection(self):
        summary = {
            "evidence": ["abc1234:secret_config.py (function signature added)"],
            "files_skipped_for_safety": ["secret_config.py"],
        }
        gates = score.check_safety_gates("clean text", summary)
        self.assertEqual(gates["fact"], "FAIL")


class TestAllowlist(unittest.TestCase):
    def test_disallowed_project_rejected(self):
        projects = allowlist.load_allowlist()
        with self.assertRaises(allowlist.AllowlistError):
            allowlist.resolve_and_validate_project("content-revenue-engine", str(REPO_ROOT / "content-revenue-engine"), projects)

    def test_path_spoofing_rejected(self):
        projects = allowlist.load_allowlist()
        with self.assertRaises(allowlist.AllowlistError):
            allowlist.resolve_and_validate_project("ai-tech-lab", str(REPO_ROOT / "content-revenue-engine"), projects)

    def test_unknown_project_rejected(self):
        projects = allowlist.load_allowlist()
        with self.assertRaises(allowlist.AllowlistError):
            allowlist.resolve_and_validate_project("does-not-exist", str(REPO_ROOT), projects)

    def test_legitimate_project_accepted(self):
        projects = allowlist.load_allowlist()
        entry, path = allowlist.resolve_and_validate_project("ai-tech-lab", str(REPO_ROOT), projects)
        self.assertEqual(path, REPO_ROOT.resolve())


# ---------------------------------------------------------------------------
# Integration tests: real Git history of this repository
# ---------------------------------------------------------------------------

class TestPipelineAgainstRealHistory(unittest.TestCase):
    """Uses this repo's own committed history — dates chosen so this test
    suite doesn't depend on today's date or future commits."""

    def setUp(self):
        projects = allowlist.load_allowlist()
        self.entry, self.repo_path = allowlist.resolve_and_validate_project("ai-tech-lab", str(REPO_ROOT), projects)

    def test_no_commits_on_date_skips(self):
        result = pipeline.run("ai-tech-lab", self.entry, self.repo_path, "2026-08-25")
        self.assertEqual(result.decision, score.SKIP)
        self.assertIsNone(result.quality_score)

    def test_notable_commit_day_produces_a_decision(self):
        result = pipeline.run("ai-tech-lab", self.entry, self.repo_path, "2026-08-22")
        self.assertIn(result.decision, (score.SKIP, score.DRAFT_ONLY, score.AUTO_PUBLISH_CANDIDATE, score.BLOCKED))
        self.assertIsNotNone(result.quality_score)
        self.assertIsNotNone(result.rendered_markdown)

    def test_duplicate_commits_already_covered_skip(self):
        # 2026-08-23's commits are already recorded in the committed
        # drafts/devlog-ai-tech-lab-2026-08-23.md fixture's source_commits.
        result = pipeline.run("ai-tech-lab", self.entry, self.repo_path, "2026-08-23")
        self.assertEqual(result.decision, score.SKIP)
        self.assertIn("既存", result.reason)

    def test_mixed_trivial_and_notable_day(self):
        # 2026-08-20 has one `chore:` commit and one `feat:` commit.
        result = pipeline.run("ai-tech-lab", self.entry, self.repo_path, "2026-08-20")
        self.assertEqual(result.stats["trivial_excluded"], 1)
        self.assertEqual(result.stats["notable_commits"], 1)


class TestDraftWriteIsolation(unittest.TestCase):
    """write_draft() must only ever write under drafts/, never _articles/."""

    def setUp(self):
        projects = allowlist.load_allowlist()
        self.entry, self.repo_path = allowlist.resolve_and_validate_project("ai-tech-lab", str(REPO_ROOT), projects)
        self.written_paths = []

    def tearDown(self):
        for p in self.written_paths:
            if p and p.exists():
                p.unlink()

    def test_write_draft_goes_to_drafts_dir_only(self):
        result = pipeline.run("ai-tech-lab", self.entry, self.repo_path, "2026-08-22")
        if result.decision not in (score.DRAFT_ONLY, score.AUTO_PUBLISH_CANDIDATE):
            self.skipTest(f"2026-08-22 did not score into a writable decision this run: {result.decision}")
        path = pipeline.write_draft(result)
        self.written_paths.append(path)
        self.assertEqual(path.parent.resolve(), (REPO_ROOT / "drafts").resolve())
        self.assertFalse((REPO_ROOT / "_articles" / path.name).exists())


class TestPromotionGate(unittest.TestCase):
    """scripts/promote-devlog.py's refusal/success logic, via its
    underlying frontmatter contract (imported directly rather than via
    subprocess, to keep this fast and dependency-free)."""

    def setUp(self):
        self.tmp_draft = REPO_ROOT / "drafts" / "__test_devlog_promotion_gate__.md"
        self.tmp_article = REPO_ROOT / "_articles" / "__test_devlog_promotion_gate__.md"

    def tearDown(self):
        for p in (self.tmp_draft, self.tmp_article):
            if p.exists():
                p.unlink()

    def _write_fixture(self, reviewer_status, publish_decision="DRAFT_ONLY"):
        from devlogkit import frontmatter as fm_lib
        fm = {
            "title": "test", "status": "draft", "permalink": "/articles/__test__/",
            "order": None, "content_type": "devlog", "development_date": "2026-01-01",
            "publish_decision": publish_decision, "reviewer_status": reviewer_status,
        }
        self.tmp_draft.write_text(fm_lib.render_markdown(fm, "body"), encoding="utf-8")

    def test_promotion_rejected_when_reviewer_pending(self):
        self._write_fixture(reviewer_status="pending")
        result = self._run_promote()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.tmp_draft.exists())
        self.assertFalse(self.tmp_article.exists())

    def test_promotion_rejected_when_decision_is_skip(self):
        self._write_fixture(reviewer_status="pass", publish_decision="SKIP")
        result = self._run_promote()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.tmp_article.exists())

    def test_promotion_succeeds_when_reviewed_and_decided(self):
        self._write_fixture(reviewer_status="pass", publish_decision="DRAFT_ONLY")
        result = self._run_promote()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.tmp_draft.exists())
        self.assertTrue(self.tmp_article.exists())

    def _run_promote(self):
        import subprocess
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "promote-devlog.py"), str(self.tmp_draft)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )


class TestMultiProjectFailureIsolation(unittest.TestCase):
    """run-daily-devlog.py's ACTUAL run_all() must not let one project's
    exception stop the others. A prior version of this test only ran a
    copy of the loop written inline here, which could never have caught a
    regression in run-daily-devlog.py itself (e.g. the real bug this
    module once had: pipeline.write_draft() was called outside the
    try/except, so an exception there — not just from pipeline.run() —
    could abort the whole multi-project loop). This version imports and
    calls the real module's run_all() so such a regression fails here."""

    def setUp(self):
        self.daily = _load_script_module("run-daily-devlog")

    def test_one_project_exception_in_pipeline_run_does_not_abort_run(self):
        projects = allowlist.load_allowlist()
        targets = list(allowlist.enabled_public_projects(projects))
        self.assertGreaterEqual(len(targets), 1, "expected at least ai-tech-lab to be enabled+public")
        # Duplicate the one real target so the loop has >1 iteration even
        # with a single-project allowlist, to prove iteration continues
        # past a failure rather than merely "returning after 1 item".
        two_targets = targets + targets

        calls = []
        original_run = pipeline.run

        def flaky_run(project_key, entry, repo_path, date_str):
            calls.append(project_key)
            if len(calls) == 1:
                raise RuntimeError("simulated failure for the first project")
            return original_run(project_key, entry, repo_path, date_str)

        self.daily.pipeline.run = flaky_run
        try:
            summary = self.daily.run_all("2026-08-25", write_mode=False, targets=two_targets)
        finally:
            self.daily.pipeline.run = original_run

        self.assertEqual(len(summary), 2, "both targets should produce a summary row despite the first failing")
        self.assertEqual(summary[0][1], "ERROR")
        self.assertNotEqual(summary[1][1], "ERROR")

    def test_exception_in_write_draft_does_not_abort_run(self):
        """Regression test for the specific bug that was found and fixed:
        write_draft() must be inside the same try/except as pipeline.run(),
        not after it."""
        projects = allowlist.load_allowlist()
        targets = list(allowlist.enabled_public_projects(projects))
        two_targets = targets + targets

        calls = []
        original_write_draft = pipeline.write_draft

        def flaky_write_draft(result):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("simulated disk error writing the first draft")
            return original_write_draft(result)

        # Force a DRAFT_ONLY-or-better decision so write_draft() actually
        # gets called; if 2026-08-22 ever scores SKIP/BLOCKED in a future
        # revision of score.py, this test would no-op rather than false-pass,
        # so assert the precondition explicitly.
        entry, repo_path = targets[0][1], targets[0][2]
        precheck = pipeline.run(targets[0][0], entry, repo_path, "2026-08-22")
        if precheck.decision not in ("DRAFT_ONLY", "AUTO_PUBLISH_CANDIDATE"):
            self.skipTest(f"2026-08-22 no longer scores into a writable decision: {precheck.decision}")

        self.daily.pipeline.write_draft = flaky_write_draft
        written = []
        try:
            summary = self.daily.run_all("2026-08-22", write_mode=True, targets=two_targets)
        finally:
            self.daily.pipeline.write_draft = original_write_draft
            # Clean up any draft the second (successful) call may have written.
            draft = REPO_ROOT / "drafts" / f"devlog-{targets[0][0]}-2026-08-22.md"
            if draft.exists():
                written.append(draft)
                draft.unlink()

        self.assertEqual(len(summary), 2)
        self.assertEqual(summary[0][1], "ERROR")
        self.assertNotEqual(summary[1][1], "ERROR")


class TestFrontmatterLeakPrevention(unittest.TestCase):
    """Regression tests for the bug where a wrapped/folded YAML frontmatter
    continuation line (produced by yaml.safe_dump for long string values)
    read as ordinary prose to _extract_docs_excerpt, because it has no
    `key:` shape for FRONTMATTER_LINE_RE to match. Fixed by tracking actual
    frontmatter line-number boundaries via the file's real `--- ... ---`
    block, independent of what any individual line looks like."""

    def test_wrapped_description_line_is_excluded_from_docs_excerpt(self):
        full_text = (
            "---\n"
            "title: test\n"
            "description: 'this is a long description that wraps across multiple\n"
            "  lines when rendered by yaml safe dump'\n"
            "---\n"
            "\n"
            "Real body prose starts here and should be extracted normally.\n"
        )
        frontmatter_range = sanitize._frontmatter_line_range(full_text)
        self.assertEqual(frontmatter_range, (1, 5))

        diff_lines = [
            "@@ -0,0 +1,7 @@",
            "+---",
            "+title: test",
            "+description: 'this is a long description that wraps across multiple",
            "+  lines when rendered by yaml safe dump'",
            "+---",
            "+",
            "+Real body prose starts here and should be extracted normally.",
        ]
        filtered = sanitize._filter_out_frontmatter_lines(diff_lines, frontmatter_range)
        excerpt = sanitize._extract_docs_excerpt(filtered)
        self.assertEqual(excerpt, "Real body prose starts here and should be extracted normally.")
        # The wrapped continuation line must not appear anywhere in the result.
        self.assertNotIn("wraps across multiple", excerpt)

    def test_no_frontmatter_block_is_a_safe_noop(self):
        # A file with no leading `---` (not all *.md files are Jekyll
        # frontmatter documents) must not have its content spuriously
        # filtered.
        self.assertIsNone(sanitize._frontmatter_line_range("Just a plain markdown file.\n"))


class TestPromotionTimeSafetyRescan(unittest.TestCase):
    """MAJOR-2 fix: promote-devlog.py and mark-devlog-reviewed.py must
    re-scan the file's CURRENT content for Security/Privacy leaks, not
    just trust a stale publish_decision/reviewer_status recorded at
    generation time — since the normal workflow expects a human to
    hand-edit the file between generation and promotion."""

    def setUp(self):
        self.tmp_draft = REPO_ROOT / "drafts" / "__test_promotion_rescan__.md"

    def tearDown(self):
        if self.tmp_draft.exists():
            self.tmp_draft.unlink()
        article = REPO_ROOT / "_articles" / "__test_promotion_rescan__.md"
        if article.exists():
            article.unlink()

    def _write_fixture(self, body):
        fm = {
            "title": "test", "status": "draft", "permalink": "/articles/__test__/",
            "order": None, "content_type": "devlog", "development_date": "2026-01-01",
            "publish_decision": "DRAFT_ONLY", "reviewer_status": "pending",
        }
        self.tmp_draft.write_text(fm_lib.render_markdown(fm, body), encoding="utf-8")

    def test_mark_reviewed_pass_rejected_if_secret_injected_after_generation(self):
        import subprocess
        self._write_fixture("clean body, then someone pastes AKIAABCDEFGHIJKLMNOP by mistake")
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "mark-devlog-reviewed.py"), str(self.tmp_draft), "--pass"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertNotEqual(result.returncode, 0)
        fm, _ = fm_lib.read_frontmatter(self.tmp_draft)
        self.assertEqual(fm["reviewer_status"], "pending", "must not have been flipped to pass")

    def test_promote_rejected_if_windows_path_present_despite_pass(self):
        import subprocess
        # Simulate: generation-time gates passed and a human marked it
        # reviewed, but the file was edited afterward to include a local
        # path (e.g. copy-pasted from a terminal) before promotion ran.
        self._write_fixture("some text mentioning C:\\Users\\jsmith\\notes\\draft.txt")
        fm, body = fm_lib.read_frontmatter(self.tmp_draft)
        fm["reviewer_status"] = "pass"
        self.tmp_draft.write_text(fm_lib.render_markdown(fm, body), encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "promote-devlog.py"), str(self.tmp_draft)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((REPO_ROOT / "_articles" / self.tmp_draft.name).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
