"""Overlay composition: upstream instructions must survive verbatim."""

from __future__ import annotations

import unittest

from omni.overlays import (
    BROKEN_REF,
    FRAMEWORK,
    OVERLAY_MARKER,
    OverlayAction,
    build_overlay,
    compose_agents_md,
)

UPSTREAM = """# Agent Instructions

## Project perspective

Keep the format small.

## Authority and boundaries

`docs/specification.mdx` is authoritative.
"""


class TestOverlayComposition(unittest.TestCase):
    def test_upstream_survives_byte_for_byte(self) -> None:
        composed = compose_agents_md(UPSTREAM)
        self.assertTrue(composed.startswith(UPSTREAM.rstrip()))
        # every upstream heading is still there, in order
        positions = [composed.index(h) for h in ("Project perspective", "Authority and boundaries")]
        self.assertEqual(positions, sorted(positions))

    def test_overlay_is_a_separate_marked_section(self) -> None:
        composed = compose_agents_md(UPSTREAM)
        self.assertIn(OVERLAY_MARKER, composed)
        self.assertLess(composed.index("Authority and boundaries"), composed.index(OVERLAY_MARKER))
        self.assertIn("ne les remplace pas", composed.replace("elle n'en remplace aucune", "ne les remplace pas"))

    def test_overlay_points_at_the_verified_framework(self) -> None:
        overlay = build_overlay()
        self.assertIn(FRAMEWORK, overlay)
        self.assertIn("OMNIBRAIN.md", overlay)

    def test_overlay_does_not_present_the_broken_reference_as_valid(self) -> None:
        overlay = build_overlay()
        self.assertIn(BROKEN_REF, overlay)          # it is named...
        self.assertIn("n'a pas pu être vérifiée", overlay)  # ...as unverifiable
        self.assertNotIn("specialized/specialized-omnibrain-orchestrator-agent.md", overlay)

    def test_composition_is_idempotent(self) -> None:
        once = compose_agents_md(UPSTREAM)
        twice = compose_agents_md(once)
        self.assertEqual(once, twice)
        self.assertEqual(once.count(OVERLAY_MARKER), 1)


class TestOverlayReporting(unittest.TestCase):
    def test_content_is_hidden_unless_requested(self) -> None:
        action = OverlayAction(
            repo="o/r", parent="up/r", branch="main", kind="refresh",
            reason="because", new_content="large payload",
        )
        self.assertNotIn("new_content", action.to_dict())
        self.assertEqual(action.to_dict(include_content=True)["new_content"], "large payload")


if __name__ == "__main__":
    unittest.main()


class TestManifest(unittest.TestCase):
    def test_manifest_is_content_free_and_hashes_the_plan(self) -> None:
        import hashlib
        import tempfile
        from pathlib import Path

        from omni.overlays import OverlayAction, write_manifest

        payload = "contenu destiné à AGENTS.md"
        action = OverlayAction(
            repo="o/r", parent="up/r", branch="main", kind="refresh",
            reason="r", new_content=payload,
        )
        skip = OverlayAction(repo="o/skip", parent="up/r", branch="main", kind="skip", reason="r")
        with tempfile.TemporaryDirectory() as tmp:
            path = write_manifest([action, skip], Path(tmp) / "plan.md", handled={"o/r": "PR #4"})
            text = path.read_text(encoding="utf-8")
        self.assertIn("`o/r`", text)
        self.assertIn("PR #4", text)
        self.assertNotIn("`o/skip`", text)                  # skipped repos stay out
        self.assertNotIn(payload, text)                     # no content leaked
        self.assertIn(hashlib.sha256(payload.encode()).hexdigest()[:16], text)
