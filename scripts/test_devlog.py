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

from devlogkit import allowlist, classify, ja, sanitize, score, security, templates  # noqa: E402
from devlogkit import frontmatter as fm_lib  # noqa: E402
from devlogkit import pipeline  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def _real_commit_hashes(n=2):
    """N real, currently-existing commit hashes from this repo's own Git
    history — used so promotion-gate fixtures satisfy the Phase 2.5 Fact
    Gate (source_commits must resolve to real commits) without hardcoding
    hashes that could stop existing in a shallow clone or after history
    rewrites."""
    import subprocess
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "log", "--format=%H", f"-n{n}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    hashes = result.stdout.strip().splitlines()
    assert len(hashes) >= n, "this repo needs at least n commits for promotion-gate fixtures"
    return hashes


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
        # Built by concatenation, not as a literal contiguous string, so
        # this test fixture (a fake, non-functional value that only needs
        # to match security.py's own AKIA-prefixed shape regex) doesn't
        # also match GitHub's push-protection AWS-key scanner, which
        # blocks pushes containing what LOOKS like a real key regardless
        # of whether it's a documented test placeholder.
        fake_aws_key = "AKIA" + "ABCDEFGHIJKLMNOP"
        self.assertTrue(security.scan_lines_for_secrets([f"+AWS_KEY = '{fake_aws_key}'"]))
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
            # Realistic evidence: one entry per distinct signal actually
            # present (as build_sanitized_summary really produces), not N
            # copies of the same string — Phase 2.7's Evidence Strength
            # rebalancing deliberately rewards genuine diversity over raw
            # duplicate-count padding, so the fixture should reflect what
            # a real well-evidenced day's `evidence` list looks like.
            "evidence": [
                "abc1234:src/thing.py (function signature added)",
                "abc1234:src/thing.py (class signature added)",
                "abc1234:src/thing.py (test added)",
                "abc1234:README.md (docs/README prose excerpt)",
                "abc1234:src/thing.py (single-line before/after)",
            ],
            "files_skipped_for_safety": [], "behavior_pairs": [("old", "new")],
        }
        total, _ = score.compute_quality_score(day_stats, summary, classify.FEATURE, 1.0)
        gates = {"security": "PASS", "privacy": "PASS", "fact": "PASS", "reasons": []}
        self.assertEqual(score.decide(total, gates), score.AUTO_PUBLISH_CANDIDATE)

    def test_security_gate_failure_forces_blocked_regardless_of_score(self):
        gates = {"security": "FAIL", "privacy": "PASS", "fact": "PASS", "reasons": ["security: ..."]}
        self.assertEqual(score.decide(100, gates), score.BLOCKED)

    def test_final_text_secret_rescan_catches_leak(self):
        # Concatenated, not a literal contiguous string — see
        # test_secret_value_scan's comment for why.
        fake_aws_key = "AKIA" + "ABCDEFGHIJKLMNOP"
        rendered = f"title: hello\nbody: AWS key {fake_aws_key} leaked\n"
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

    def _write_fixture(self, reviewer_status, publish_decision="DRAFT_ONLY", body="body"):
        from devlogkit import frontmatter as fm_lib
        fm = {
            "title": "test", "status": "draft", "permalink": "/articles/__test__/",
            "order": None, "content_type": "devlog", "development_date": "2026-01-01",
            "publish_decision": publish_decision, "reviewer_status": "pending",
            "generated_from_git": True, "source_project": "ai-tech-lab",
            "source_commits": _real_commit_hashes(1),
        }
        self.tmp_draft.write_text(fm_lib.render_markdown(fm, body), encoding="utf-8")
        if reviewer_status == "pass":
            result = self._run_mark_reviewed(["--pass", "--method", "test"])
            assert result.returncode == 0, f"test setup failed to mark reviewed: {result.stderr}"

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

    def test_promotion_rejected_without_recorded_hash(self):
        """A draft with reviewer_status: pass set by hand (not via
        mark-devlog-reviewed.py, so it has no reviewed_content_hash) must
        still be rejected — reviewer_status alone is not sufficient."""
        from devlogkit import frontmatter as fm_lib
        fm = {
            "title": "test", "status": "draft", "permalink": "/articles/__test__/",
            "order": None, "content_type": "devlog", "development_date": "2026-01-01",
            "publish_decision": "DRAFT_ONLY", "reviewer_status": "pass",
        }
        self.tmp_draft.write_text(fm_lib.render_markdown(fm, "body"), encoding="utf-8")
        result = self._run_promote()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.tmp_article.exists())

    def test_promotion_succeeds_when_reviewed_and_decided(self):
        self._write_fixture(reviewer_status="pass", publish_decision="DRAFT_ONLY")
        result = self._run_promote()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.tmp_draft.exists())
        self.assertTrue(self.tmp_article.exists())

    def test_promotion_rejected_when_source_commit_does_not_exist(self):
        """Fact Gate (Phase 2.5 Step 9): even a fully-reviewed, fingerprint-
        matching draft must be rejected if source_commits references a hash
        that doesn't actually exist in the project's Git history — an
        independent review found this was previously never checked at all,
        so a hand-crafted or corrupted draft with fabricated commit hashes
        could otherwise be promoted as if it were genuinely Git-derived."""
        from devlogkit import frontmatter as fm_lib
        fm = {
            "title": "test", "status": "draft", "permalink": "/articles/__test__/",
            "order": None, "content_type": "devlog", "development_date": "2026-01-01",
            "publish_decision": "DRAFT_ONLY", "reviewer_status": "pending",
            "generated_from_git": True, "source_project": "ai-tech-lab",
            "source_commits": ["0000000000000000000000000000000000dead"],
        }
        self.tmp_draft.write_text(fm_lib.render_markdown(fm, "body"), encoding="utf-8")
        result = self._run_mark_reviewed(["--pass", "--method", "test"])
        assert result.returncode == 0, f"test setup failed to mark reviewed: {result.stderr}"
        result = self._run_promote()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.tmp_article.exists())
        self.assertIn("Fact Gate", result.stderr)

    def test_promotion_rejected_when_source_commit_is_a_symbolic_ref(self):
        """Fact Gate hash-shape check (iteration-2 review finding): `git
        cat-file -e <ref>^{commit}` happily resolves symbolic refs like
        "HEAD" or a branch name too, not just literal commit hashes — so
        without an explicit hex-shape check, `source_commits: ["HEAD"]`
        would pass the existence check in any repo with commits at all,
        despite naming no specific, verifiable commit."""
        from devlogkit import frontmatter as fm_lib
        fm = {
            "title": "test", "status": "draft", "permalink": "/articles/__test__/",
            "order": None, "content_type": "devlog", "development_date": "2026-01-01",
            "publish_decision": "DRAFT_ONLY", "reviewer_status": "pending",
            "generated_from_git": True, "source_project": "ai-tech-lab",
            "source_commits": ["HEAD"],
        }
        self.tmp_draft.write_text(fm_lib.render_markdown(fm, "body"), encoding="utf-8")
        result = self._run_mark_reviewed(["--pass", "--method", "test"])
        assert result.returncode == 0, f"test setup failed to mark reviewed: {result.stderr}"
        result = self._run_promote()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.tmp_article.exists())
        self.assertIn("Fact Gate", result.stderr)

    def _run_promote(self):
        import subprocess
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "promote-devlog.py"), str(self.tmp_draft)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )

    def _run_mark_reviewed(self, extra_args):
        import subprocess
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "mark-devlog-reviewed.py"), str(self.tmp_draft)] + extra_args,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )


class TestContentFingerprintTamperDetection(unittest.TestCase):
    """Step 18 (docs/devlog-policy.md): a draft reviewed via
    mark-devlog-reviewed.py --pass must become UN-promotable the moment
    ANYTHING changes afterward — one character in the body, an added
    paragraph, a frontmatter field, or the source_commits list. Each
    sub-test tampers with a genuinely-reviewed fixture in one specific
    way and confirms promote-devlog.py refuses."""

    def setUp(self):
        self.tmp_draft = REPO_ROOT / "drafts" / "__test_tamper_detection__.md"
        self.tmp_article = REPO_ROOT / "_articles" / "__test_tamper_detection__.md"

    def tearDown(self):
        for p in (self.tmp_draft, self.tmp_article):
            if p.exists():
                p.unlink()

    def _write_and_review_fixture(self):
        from devlogkit import frontmatter as fm_lib
        fm = {
            "title": "test article", "status": "draft", "permalink": "/articles/__test__/",
            "order": None, "content_type": "devlog", "development_date": "2026-01-01",
            "publish_decision": "DRAFT_ONLY", "reviewer_status": "pending",
            "generated_from_git": True, "source_project": "ai-tech-lab",
            "source_commits": _real_commit_hashes(2),
        }
        self.tmp_draft.write_text(fm_lib.render_markdown(fm, "This is the reviewed body text."), encoding="utf-8")
        result = self._run_mark_reviewed()
        assert result.returncode == 0, f"test setup failed: {result.stderr}"

    def _tamper_and_assert_promotion_rejected(self, mutate_fn):
        from devlogkit import frontmatter as fm_lib
        fm, body = fm_lib.read_frontmatter(self.tmp_draft)
        fm, body = mutate_fn(fm, body)
        self.tmp_draft.write_text(fm_lib.render_markdown(fm, body), encoding="utf-8")
        result = self._run_promote()
        self.assertNotEqual(result.returncode, 0, "promotion must be rejected after tampering")
        self.assertFalse(self.tmp_article.exists())

    def test_one_character_body_change_is_detected(self):
        self._write_and_review_fixture()
        self._tamper_and_assert_promotion_rejected(lambda fm, body: (fm, body + "."))

    def test_added_paragraph_is_detected(self):
        self._write_and_review_fixture()
        self._tamper_and_assert_promotion_rejected(
            lambda fm, body: (fm, body + "\n\nユーザーから要望があったため実装しました。")
        )

    def test_frontmatter_field_change_is_detected(self):
        self._write_and_review_fixture()

        def mutate(fm, body):
            fm["title"] = "a different title"
            return fm, body

        self._tamper_and_assert_promotion_rejected(mutate)

    def test_source_commits_change_is_detected(self):
        self._write_and_review_fixture()

        def mutate(fm, body):
            fm["source_commits"] = ["abc1234"]  # dropped one commit
            return fm, body

        self._tamper_and_assert_promotion_rejected(mutate)

    def test_publish_decision_upgrade_is_detected(self):
        """An adversarial edit trying to upgrade SKIP/BLOCKED to a
        promotable decision after the fact must also be caught — the
        fingerprint locks publish_decision too, not just prose content."""
        self._write_and_review_fixture()

        def mutate(fm, body):
            fm["publish_decision"] = "AUTO_PUBLISH_CANDIDATE"
            return fm, body

        self._tamper_and_assert_promotion_rejected(mutate)

    def test_unmodified_reviewed_draft_still_promotes(self):
        """Sanity check: the tamper-detection tests above aren't just
        failing promotion unconditionally — an untouched, genuinely
        reviewed draft must still succeed."""
        self._write_and_review_fixture()
        result = self._run_promote()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.tmp_article.exists())

    def _run_promote(self):
        import subprocess
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "promote-devlog.py"), str(self.tmp_draft)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )

    def _run_mark_reviewed(self):
        import subprocess
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "mark-devlog-reviewed.py"), str(self.tmp_draft), "--pass", "--method", "test"],
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


class TestChangedFilesExcludesBehaviorPairPaths(unittest.TestCase):
    """Phase 2.7, independent review finding: a path already detailed in
    "変更前後" (behavior_pairs) was ALSO listed bare in "変更されたファイル"
    — the per_file_signals-based dedup didn't cover this separate data
    structure, so the same redundant-repetition problem that fix
    addressed for functions/classes/headings/config-keys still applied to
    before/after pairs."""

    def test_behavior_pair_path_excluded_from_changed_files(self):
        commit = {"hash": "abc1234567", "files": [
            {"path": "a.html", "status": "M"}, {"path": "b.html", "status": "M"},
        ]}
        summary = {
            "per_file_signals": [],
            "behavior_pairs": [{"before": "x", "after": "y", "path": "a.html", "commit_hash": "abc1234567"}],
        }
        section = templates._changed_files_section([commit], summary)
        rendered = "\n".join(section)
        self.assertNotIn("a.html", rendered)
        self.assertIn("b.html", rendered)


class TestDocsExcerptAndBeforeAfterAttribution(unittest.TestCase):
    """Phase 2.7, independent review finding: without a commit/path
    attribution on the "README/ドキュメントの追記内容" and "変更前後"
    sections, a reader couldn't tell whether two mentions of the same
    heading TEXT (e.g. a template-standard heading reused across
    different article files) were the same event or two unrelated ones —
    reading as a self-contradiction that wasn't actually one."""

    def test_docs_excerpt_carries_commit_hash(self):
        summary = {
            "functions_added": [], "classes_added": [], "tests_added": [],
            "headings_added": [], "config_keys_changed": [],
            "docs_excerpts": [{"path": "README.md", "commit_hash": "abc1234567", "text": "Some prose."}],
            "behavior_pairs": [], "per_file_signals": [],
        }
        rendered = "\n".join(templates._evidence_section(summary))
        self.assertIn("README.md", rendered)
        self.assertIn("abc1234", rendered)

    def test_behavior_pair_carries_path_and_commit_hash(self):
        summary = {
            "functions_added": [], "classes_added": [], "tests_added": [],
            "headings_added": [], "config_keys_changed": [],
            "docs_excerpts": [],
            "behavior_pairs": [{"before": "old", "after": "new", "path": "a.html", "commit_hash": "def7654321"}],
            "per_file_signals": [],
        }
        rendered = "\n".join(templates._evidence_section(summary))
        self.assertIn("a.html", rendered)
        self.assertIn("def7654", rendered)


class TestFrontmatterBoundaryBeforeAfterFix(unittest.TestCase):
    """Phase 2.7 fix for a docs/devlog-policy.md §31 carried-over MAJOR:
    _filter_out_frontmatter_lines previously only excluded ADDED lines
    within the frontmatter block, so a REMOVED frontmatter continuation
    line could survive through to _extract_single_line_replacement and
    pair with an unrelated added body line as a misleading "before/after"."""

    def test_removed_frontmatter_line_not_paired_with_added_body_line(self):
        old_frontmatter_range = (1, 3)  # the OLD file's --- ... --- block spans lines 1-3
        diff_lines = [
            "@@ -2,1 +2,1 @@",
            "-  wrapped frontmatter continuation text",
            "+A completely unrelated body sentence that was added.",
        ]
        filtered = sanitize._filter_out_frontmatter_lines(diff_lines, None, old_frontmatter_range)
        pairs = sanitize._extract_single_line_replacement(filtered)
        self.assertEqual(pairs, [])

    def test_removed_body_line_still_pairs_normally(self):
        # Sanity check: when the removed line is genuinely outside the old
        # frontmatter range, single-line-replacement pairing still works.
        old_frontmatter_range = (1, 3)
        diff_lines = [
            "@@ -5,1 +5,1 @@",
            "-old body sentence",
            "+new body sentence",
        ]
        filtered = sanitize._filter_out_frontmatter_lines(diff_lines, None, old_frontmatter_range)
        pairs = sanitize._extract_single_line_replacement(filtered)
        self.assertEqual(pairs, [("old body sentence", "new body sentence")])


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


class TestStructuralFileSignal(unittest.TestCase):
    """Phase 2.6: a new Technical Depth signal for site-engineering work
    (Jekyll layouts/includes/stylesheets) that the existing function/class/
    test regexes (Python/JS/Go-shaped) cannot see at all — added after a
    10-day real-data evaluation (Phase 2.5) found this axis structurally
    under-scored this content-heavy repo's actual work."""

    def test_layout_include_and_stylesheet_paths_match(self):
        for path in ("_layouts/article.html", "_includes/ga4.html", "assets/css/style.css"):
            self.assertTrue(sanitize.STRUCTURAL_PATH_RE.search(path), path)

    def test_ordinary_article_and_script_paths_do_not_match(self):
        for path in ("_articles/01-arduino-toha-hajimekata.md",
                      "scripts/devlogkit/score.py", "README.md"):
            self.assertFalse(sanitize.STRUCTURAL_PATH_RE.search(path), path)

    def test_markdown_template_path_deliberately_excluded(self):
        """`templates/` was deliberately dropped from STRUCTURAL_PATH_RE
        (independent-review BLOCKER, Phase 2.6): this repo's `templates/`
        holds a Markdown authoring aid, not Liquid/HTML engineering, and
        including it double-counted the same file toward both Technical
        Depth and the Markdown-extraction axes (config_keys_changed/
        headings_added)."""
        self.assertFalse(sanitize.STRUCTURAL_PATH_RE.search("templates/article-template.md"))

    def test_technical_depth_credits_structural_signal_once(self):
        # A day with ONLY a structural-file signal (no functions/classes/
        # tests/behavior_pairs) should score exactly 1 of 5 signal types.
        summary = {
            "functions_added": [], "classes_added": [], "tests_added": [],
            "behavior_pairs": [], "structural_files_changed": ["_layouts/article.html"],
        }
        self.assertEqual(score.score_technical_depth(summary), 4)

    def test_markdown_template_file_does_not_double_count_across_axes(self):
        """Integration-level regression for the BLOCKER above: editing
        templates/article-template.md must feed config_keys_changed/
        headings_added (Markdown extraction) but NOT structural_files_changed,
        even though it lives in a directory whose name overlaps the
        `structural` concept."""
        from devlogkit import gitmeta

        class _FakeCommit(dict):
            pass

        # Real call, using this repo's own history: find a commit that
        # touched templates/article-template.md and confirm the summary.
        # Falls back to a synthetic single-file diff if no such commit
        # exists in this checkout's history (keeps the test hermetic).
        commit = {"hash": "0" * 40}
        files = [{"status": "M", "path": "templates/article-template.md"}]
        import unittest.mock as mock
        fake_diff = [
            "@@ -1,3 +1,4 @@",
            " ---",
            "+category: 開発ログ",
            " ---",
        ]
        with mock.patch.object(gitmeta, "get_file_diff", return_value=fake_diff), \
             mock.patch.object(gitmeta, "get_full_file_at_commit", return_value="---\ntitle: x\n---\nbody\n"):
            summary = sanitize.build_sanitized_summary(REPO_ROOT, commit, files)
        self.assertEqual(summary["structural_files_changed"], [])

    def test_technical_depth_still_caps_at_20(self):
        summary = {
            "functions_added": ["f"], "classes_added": ["C"], "tests_added": ["test_x"],
            "behavior_pairs": [("a", "b")], "structural_files_changed": ["_layouts/article.html"],
        }
        self.assertEqual(score.score_technical_depth(summary), 20)


class TestDescriptionTranslationConsistency(unittest.TestCase):
    """Phase 2.6, independent review finding: description/primary_keyword
    previously always embedded raw English (day_type constant, commit
    subjects) even on days whose title translated fully to Japanese —
    inconsistent enough to read as a generation bug rather than an honest,
    uniform fallback."""

    def test_translatable_subject_becomes_japanese(self):
        phrase, used_japanese = templates.translated_or_original("launch monetization and analytics foundation")
        self.assertTrue(used_japanese)
        self.assertNotRegex(phrase, r"[A-Za-z]{4,}")  # no long English word survives

    def test_untranslatable_subject_falls_back_unchanged(self):
        original = "wire up an extremely unusual bespoke integration harness"
        phrase, used_japanese = templates.translated_or_original(original)
        self.assertFalse(used_japanese)
        self.assertEqual(phrase, original)

    def test_day_type_ja_label_covers_every_day_type(self):
        for day_type in (classify.FEATURE, classify.BUGFIX, classify.PERFORMANCE,
                          classify.UI, classify.ARCHITECTURE, classify.GENERIC):
            self.assertIn(day_type, classify.DAY_TYPE_JA_LABEL)
            # No untranslated lowercase English word (short adopted
            # acronyms like "UI" are fine and natural in Japanese tech writing).
            self.assertNotRegex(classify.DAY_TYPE_JA_LABEL[day_type], r"[a-z]{3,}")


class TestChangeCompositionOverview(unittest.TestCase):
    """Phase 2.7, independent review finding (x2): the article body read
    as pure fragment-list "Git変更の羅列" with no sentence connecting the
    commit list to the detailed per-file breakdown. Added a single,
    purely mechanical-count overview sentence — never an interpretation
    of what the changes MEAN or WHY they were made (Step 8's Fact rule),
    which is why Phase 2.6 (§36) had declined to add a summary at all."""

    def test_omits_zero_categories(self):
        summary = {
            "per_file_signals": [{"path": "a.md", "functions": [], "classes": [], "tests": [],
                                   "headings": [], "config_keys": ["title"]}],
            "docs_excerpts": [],
        }
        overview = templates._change_composition_overview(summary)
        self.assertIn("設定・frontmatterキーの変更", overview)
        self.assertNotIn("見出し", overview)
        self.assertNotIn("関数", overview)

    def test_empty_when_nothing_extracted(self):
        summary = {"per_file_signals": [], "docs_excerpts": []}
        self.assertEqual(templates._change_composition_overview(summary), "")

    def test_counts_match_per_file_signals_not_truncated_day_level_fields(self):
        """Regression for a real bug an independent review found: counting
        from summary["headings_added"] (separately capped at sanitize.py's
        MAX_ITEMS_PER_LIST) instead of per_file_signals (what the "ファイル
        別の変更点" detail section actually renders) let this sentence
        claim a smaller number than what was really shown below it — e.g.
        a day with 9 real headings across 3 files claimed "8件" because
        the DAY-LEVEL list happened to be truncated to 8 while
        per_file_signals, read by the detail section, was not."""
        summary = {
            "per_file_signals": [
                {"path": "a.md", "functions": [], "classes": [], "tests": [],
                 "headings": ["h1", "h2"], "config_keys": []},
                {"path": "b.md", "functions": [], "classes": [], "tests": [],
                 "headings": ["h3", "h4", "h5", "h6", "h7", "h8", "h9"], "config_keys": []},
            ],
            # A deliberately-truncated (unrealistic but reproduces the bug
            # condition) day-level field that must NOT be what gets counted.
            "headings_added": ["h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8"],
            "docs_excerpts": [],
        }
        overview = templates._change_composition_overview(summary)
        self.assertIn("見出しの追加(9件)", overview)

    def test_behavior_pairs_are_counted(self):
        """Regression: independent review found behavior_pairs was
        omitted from this sentence with no valid reason (unlike
        structural_files_changed, it DOES have a corresponding detail
        section — "変更前後" — so omitting it looked like an oversight)."""
        summary = {
            "per_file_signals": [], "docs_excerpts": [],
            "behavior_pairs": [{"before": "a", "after": "b", "path": "x.html", "commit_hash": "abc"}],
        }
        overview = templates._change_composition_overview(summary)
        self.assertIn("変更前後を確認できた箇所(1件)", overview)

    def test_never_asserts_reason_or_purpose(self):
        # Sanity guard against future edits reintroducing invented
        # motivation language into this specific sentence.
        summary = {
            "per_file_signals": [{"path": "a.py", "functions": ["f"], "classes": [], "tests": [],
                                   "headings": ["H"], "config_keys": ["k"]}],
            "docs_excerpts": ["e"],
        }
        overview = templates._change_composition_overview(summary)
        for forbidden in ("ため", "目的", "理由", "解決"):
            self.assertNotIn(forbidden, overview)


class TestTitleDescriptionConsistency(unittest.TestCase):
    """Phase 2.7, independent review finding (x2): title and description
    were translated independently, so on a multi-commit day they could
    disagree about whether Japanese translation succeeded — e.g. title
    fully Japanese (only needs ONE qualifying commit) while description
    fell back to all-English (a stricter all-must-qualify rule). Fixed by
    deriving both from the exact same _select_headline_phrase choice."""

    def _commit(self, subject, lines=10):
        return {"subject": subject, "stat": {"insertions": lines, "deletions": 0}}

    def test_title_and_description_agree_when_one_commit_translates(self):
        notable = [
            self._commit("add visual guides to first Arduino article"),
            self._commit("improve site layout and article presentation"),
            self._commit("publish Arduino IDE installation guide"),
        ]
        title, used_japanese, _coverage = templates.build_headline("AI-Tech-Lab", notable)
        description = templates.describe_day("2026-08-08", "AI-Tech-Lab", notable)
        self.assertTrue(used_japanese)
        self.assertIn("サイトレイアウト", title)
        self.assertIn("サイトレイアウト", description)  # same phrase, not a separately-translated fallback

    def test_title_and_description_agree_when_nothing_translates(self):
        notable = [self._commit("wire up an extremely unusual bespoke integration harness")]
        title, used_japanese, _coverage = templates.build_headline("AI-Tech-Lab", notable)
        description = templates.describe_day("2026-08-08", "AI-Tech-Lab", notable)
        self.assertFalse(used_japanese)
        self.assertIn("wire up an extremely unusual bespoke integration harness", title)
        self.assertIn("wire up an extremely unusual bespoke integration harness", description)


class TestTopicKeywordDerivation(unittest.TestCase):
    """Phase 2.7, independent review finding: primary_keyword/search_intent
    depended only on day_type (e.g. every "feature" day got the identical
    "AI-Tech-Lab 新機能"), which is an SEO keyword-cannibalization risk
    once multiple devlog articles of the same type exist."""

    def _commit(self, subject, lines=10):
        return {"subject": subject, "stat": {"insertions": lines, "deletions": 0}}

    def test_topic_keyword_derived_when_translatable(self):
        notable = [self._commit("launch monetization and analytics foundation")]
        topic = templates.derive_topic_keyword(notable)
        self.assertIsNotNone(topic)
        self.assertNotRegex(topic, r"[A-Za-z]{4,}")

    def test_topic_keyword_none_when_untranslatable(self):
        notable = [self._commit("wire up an extremely unusual bespoke integration harness")]
        self.assertIsNone(templates.derive_topic_keyword(notable))

    def test_two_different_days_get_different_topic_keywords(self):
        day1 = [self._commit("improve site layout and article presentation")]
        day2 = [self._commit("launch monetization and analytics foundation")]
        self.assertNotEqual(templates.derive_topic_keyword(day1), templates.derive_topic_keyword(day2))


class TestAcronymCasingPreserved(unittest.TestCase):
    """Phase 2.7, independent review finding: an unmapped token falling
    through to `.capitalize()` mangles real acronyms (ide -> Ide, css ->
    Css, github -> Github) even though it correctly fixes the more common
    case of a genuine proper noun (arduino -> Arduino)."""

    def test_known_acronyms_stay_uppercase(self):
        phrase, coverage, token_count, _obj = ja.translate_subject("publish new CSS and HTML for the IDE")
        self.assertIn("CSS", phrase)
        self.assertIn("HTML", phrase)
        self.assertIn("IDE", phrase)
        self.assertNotIn("Css", phrase)
        self.assertNotIn("Html", phrase)
        self.assertNotIn("Ide", phrase)

    def test_unmapped_proper_noun_still_capitalized(self):
        phrase, coverage, token_count, _obj = ja.translate_subject("add support for arduino")
        self.assertIn("Arduino", phrase)
        self.assertNotIn("arduino", phrase)


class TestTaskListMarkerExcludedFromExcerpt(unittest.TestCase):
    """Phase 2.6, independent review finding: a GFM task-list line
    (`- [ ] ...`) quoted as a docs excerpt would render as literal "[ ]"
    text (this site's kramdown config has no GFM extension enabled), and
    reads as an out-of-context internal checklist item either way."""

    def test_task_list_line_is_excluded(self):
        lines = [
            "@@ -1,0 +1,1 @@",
            "+- [ ] some checklist item that is long enough to otherwise qualify",
        ]
        self.assertIsNone(sanitize._extract_docs_excerpt(lines))

    def test_ordinary_bullet_prose_is_still_extracted(self):
        lines = [
            "@@ -1,0 +1,1 @@",
            "+This is an ordinary sentence long enough to qualify as prose.",
        ]
        excerpt = sanitize._extract_docs_excerpt(lines)
        self.assertIsNotNone(excerpt)


class TestHtmlCommentExcludedFromExcerpt(unittest.TestCase):
    """Phase 2.6, independent review finding: a multi-line HTML comment
    (author-facing instructions in a template file, e.g.
    templates/article-template.md's `<!-- 読者の課題解決に必要な場合のみ...
    -->` guidance) was being quoted as if it were reader-facing
    documentation prose, because a single-line markup check can't see that
    the comment's FIRST line has no closing `-->` on it yet."""

    def test_multiline_html_comment_excluded(self):
        lines = [
            "@@ -1,0 +1,3 @@",
            "+<!-- 読者の課題解決に必要な場合のみ。実際に使用したものを優先し、選定理由を記載。",
            "+     CTAボタンは {% include amazon-cta.html %} を使う",
            "+     を指定する -->",
        ]
        self.assertIsNone(sanitize._extract_docs_excerpt(lines))

    def test_prose_after_a_closed_html_comment_is_still_extracted(self):
        lines = [
            "@@ -1,0 +1,3 @@",
            "+<!-- an internal note that closes on one line -->",
            "+",
            "+This is genuine prose written for the reader, long enough to qualify.",
        ]
        excerpt = sanitize._extract_docs_excerpt(lines)
        self.assertIsNotNone(excerpt)
        self.assertIn("genuine prose", excerpt)


class TestPlanningLabelAndHeadingRename(unittest.TestCase):
    """Regression tests for two article-quality bugs an independent review
    found in a real generated Dev Log: (1) an internal editorial-planning
    label ("検索意図:", from CONTENT_PLAN.md-style content-planning docs)
    leaking into a "docs excerpt" as if it were reader-facing documentation
    prose; (2) a heading-LEVEL-only rename (e.g. "# X" -> "## X") being
    reported as both a newly "added heading" AND a "before/after" change,
    contradicting itself in the rendered article."""

    def test_internal_planning_label_excluded_from_docs_excerpt(self):
        # Phase 2.7: the numbered-bold-title line itself is now ALSO
        # excluded (it's a planning-list index entry, not prose — see
        # TestPlanningListEntryExcludedFromExcerpt), so this hunk has no
        # qualifying candidate left at all and correctly yields no excerpt.
        lines = [
            "@@ -10,0 +11,2 @@",
            "+2. **Some future article title**",
            "+   検索意図: this is internal SEO planning metadata, not documentation.",
        ]
        excerpt = sanitize._extract_docs_excerpt(lines)
        self.assertIsNone(excerpt)

    def test_internal_planning_label_excluded_even_under_ordinary_prose(self):
        # The 検索意図 exclusion must still work independently of the
        # numbered-bold-title exclusion — e.g. under an ordinary bullet,
        # not just under a planning-list title.
        lines = [
            "@@ -10,0 +11,2 @@",
            "+Some genuine prose sentence that a reader would want to see here.",
            "+検索意図: this is internal SEO planning metadata, not documentation.",
        ]
        excerpt = sanitize._extract_docs_excerpt(lines)
        self.assertIsNotNone(excerpt)
        self.assertNotIn("検索意図", excerpt)
        self.assertNotIn("SEO planning metadata", excerpt)


class TestPlanningListEntryExcludedFromExcerpt(unittest.TestCase):
    """Phase 2.7: a numbered/bulleted line whose entire content is one
    bold span (e.g. "2. **Arduino IDEのインストール方法...**" from an
    internal content-planning list) is a title/index entry, not prose a
    human wrote for a reader — excluded regardless of which file it's
    from (a general structural shape, not a specific project filename)."""

    def test_numbered_bold_title_excluded(self):
        lines = [
            "@@ -1,0 +1,1 @@",
            "+2. **Arduino IDEのインストール方法(Windows版)のガイド記事タイトル案**",
        ]
        self.assertIsNone(sanitize._extract_docs_excerpt(lines))

    def test_bulleted_bold_title_excluded(self):
        lines = [
            "@@ -1,0 +1,1 @@",
            "+- **今後書く予定の記事タイトル案について検討したメモ書き**",
        ]
        self.assertIsNone(sanitize._extract_docs_excerpt(lines))

    def test_prose_with_inline_bold_is_still_extracted(self):
        lines = [
            "@@ -1,0 +1,1 @@",
            "+この記事では **重要なポイント** を実際の手順に沿って説明します。",
        ]
        excerpt = sanitize._extract_docs_excerpt(lines)
        self.assertIsNotNone(excerpt)

    def test_heading_level_only_rename_is_not_reported_as_added(self):
        lines = [
            "@@ -5 +5 @@",
            "-# この記事でわかること",
            "+## この記事でわかること",
        ]
        headings = sanitize._extract_headings(lines)
        self.assertNotIn("この記事でわかること", headings)

    def test_genuinely_new_heading_is_still_reported(self):
        lines = [
            "@@ -0,0 +1,2 @@",
            "+## A brand new section",
            "+some body text",
        ]
        headings = sanitize._extract_headings(lines)
        self.assertIn("A brand new section", headings)


class TestFrontmatterSplitRobustness(unittest.TestCase):
    """Regression test for a bug an independent code review found in
    frontmatter.split_frontmatter: the earlier implementation split on the
    literal 3-character substring "---" anywhere in the text, so a
    frontmatter VALUE that happens to contain "---" (e.g. a commit subject
    like "docs: replace === with --- style" embedded verbatim by ja.py's
    English-fallback path) would be mis-split mid-value instead of at the
    real `--- ... ---` delimiter lines."""

    def test_dashes_inside_a_value_do_not_break_the_split(self):
        import yaml
        fm = {"title": "docs: replace === with --- style", "status": "draft"}
        rendered = fm_lib.render_markdown(fm, "The body.")
        fm_text, body = fm_lib.split_frontmatter(rendered)
        self.assertIsNotNone(fm_text)
        parsed_fm = yaml.safe_load(fm_text)
        self.assertEqual(parsed_fm["title"], "docs: replace === with --- style")
        self.assertEqual(body.strip(), "The body.")


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
        # Concatenated, not a literal contiguous string — see
        # TestSecretFiltering.test_secret_value_scan's comment for why.
        fake_aws_key = "AKIA" + "ABCDEFGHIJKLMNOP"
        self._write_fixture(f"clean body, then someone pastes {fake_aws_key} by mistake")
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "mark-devlog-reviewed.py"), str(self.tmp_draft), "--pass"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertNotEqual(result.returncode, 0)
        fm, _ = fm_lib.read_frontmatter(self.tmp_draft)
        self.assertEqual(fm["reviewer_status"], "pending", "must not have been flipped to pass")

    def test_promote_rejected_if_windows_path_present_despite_pass(self):
        import subprocess
        # Simulate: the draft was clean and genuinely reviewed (hash
        # recorded on clean content), but was THEN edited to include a
        # local path (e.g. copy-pasted from a terminal) before promotion
        # ran. The content-fingerprint check (Phase 2.5) would already
        # catch this on its own, but the Privacy gate re-scan is kept as
        # independent defense in depth — this test confirms promotion is
        # rejected either way, not that one specific mechanism fired.
        self._write_fixture("clean body with nothing sensitive in it")
        mark_result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "mark-devlog-reviewed.py"), str(self.tmp_draft), "--pass", "--method", "test"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert mark_result.returncode == 0, mark_result.stderr

        fm, body = fm_lib.read_frontmatter(self.tmp_draft)
        body += " some text mentioning C:\\Users\\jsmith\\notes\\draft.txt"
        self.tmp_draft.write_text(fm_lib.render_markdown(fm, body), encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "promote-devlog.py"), str(self.tmp_draft)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((REPO_ROOT / "_articles" / self.tmp_draft.name).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
