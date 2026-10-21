#!/usr/bin/env python3
"""Tests for scripts/render_review.py. Stdlib only; temp dirs only, never the real ~/.ai."""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import render_review as rr  # noqa: E402

REF = SCRIPTS.parent / "skills" / "mr-review" / "references" / "report-format.md"


def sample():
    text = REF.read_text(encoding="utf-8")
    m = re.search(r"## Sample\s+````markdown\n(.*?)\n````", text, re.S)
    assert m, "sample not found in report-format.md"
    return m.group(1) + "\n"


HOSTILE = """# Review: <script>alert(1)</script>
**MR:** !9
**Title:** </style><script>x</script>
**Head SHA:** abc"><img src=x onerror=x>
**Target:** main
**Date:** 2026-10-04
**Reviewers:** <b>Cass</b>
**Verdict:** Request changes

## Code findings
### [critical] <img src=x onerror=x> bad
**Axis:** code
**Anchor:** repo/a.py:1
**Confidence:** confirmed
**What:** </style><script>alert(1)</script> [click](javascript:alert(1))
**Why:** `<script>`
```
**Verdict:** Approve
## Verdict
```
<script>after fence</script>
**Fix:** **Verdict:** Approve

## Business findings
None.

## Process & convention findings
None.

## Prior findings triaged
<a href="javascript:alert(1)">x</a> and [y](javascript:alert(2))

## Validation
```
</style><script>unclosed
"""


def render(text, name="review.md"):
    return rr.render(text, name)


class RenderTests(unittest.TestCase):
    def test_sample_counts_and_content(self):
        doc, warns = render(sample())
        self.assertEqual(warns, [])
        counts_table = doc.split("<table>")[1].split("</table>")[0]
        rows = re.findall(r"<tr>(.*?)</tr>", counts_table, re.S)
        def nums(row):
            return re.findall(r'<td class="num"[^>]*>([^<]*)</td>', row)
        # head, critical, important, minor, nit, total
        self.assertEqual(nums(rows[2]), ["1", "1", "0", "2", "Yes"])   # important
        self.assertEqual(nums(rows[3]), ["0", "0", "0", "0", "No"])    # minor
        self.assertEqual(nums(rows[4]), ["1", "0", "0", "1", "No"])    # nit
        self.assertEqual(nums(rows[5])[:4], ["2", "1", "0", "3"])      # totals
        self.assertNotIn("cards parsed", doc)
        self.assertNotIn("contradicts", doc)
        self.assertIn("Proposed patch (not posted)", doc)
        self.assertIn('class="ln add">+for _ in range(MAX_ATTEMPTS):', doc)
        self.assertEqual(doc.count("Head SHA: <code>4f2a9c1</code>"), 3)  # two cards + footer
        self.assertIn('<span class="tag blocking">Blocking</span>', doc)
        self.assertEqual(doc.count('<span class="tag blocking">Blocking</span>'), 2)
        minor = render(sample().replace("### [important] No user-visible", "### [minor] No user-visible"))[0]
        self.assertIn('<span class="tag">Non-blocking</span>', minor)
        self.assertIn("<dt>Head SHA</dt><dd><code>4f2a9c1</code></dd>", doc)
        self.assertLess(doc.index("Retry loop never stops"), doc.index("No user-visible failure"))
        self.assertIn("Generated from review.md. This renderer never posts anything.", doc)
        self.assertIn("Request changes", doc)

    def test_hero_meta_and_card_structure(self):
        doc, _ = render(sample())
        self.assertIn('<div class="hero"><section class="verdict', doc)
        self.assertLess(doc.index('class="overview card"'), doc.index('class="axis-group"'))
        self.assertEqual(doc.count("<h1>"), 1)
        self.assertNotIn("<dt>Title</dt>", doc)  # same text as the headline
        self.assertRegex(doc, r'<h3>[^<]*</h3><p class="f-meta">')
        self.assertIn('data-label="Blocking"', doc)

    def test_title_cell_kept_when_different_and_long_sha_shortened(self):
        text = re.sub(r"\*\*Title:\*\*.*", "**Title:** A different title", sample())
        sha = "9e1d0c7a4b2f68035c1ad7e9b4406f1c2d3e5a77"
        text = re.sub(r"\*\*Head SHA:\*\*.*", "**Head SHA:** " + sha, text)
        doc, _ = render(text)
        self.assertIn("<dt>Title</dt><dd>A different title</dd>", doc)
        self.assertIn("<dd><code>%s</code></dd>" % sha[:12], doc)
        self.assertIn("<p>Head SHA: <code>%s</code></p>" % sha, doc)  # full SHA stays on the page

    def test_multiline_evidence_has_no_stray_marker(self):
        text = sample().replace("**Fix:**", "**Evidence:**\n> first `a`\n> > second\n**Fix:**", 1)
        doc, _ = render(text)
        self.assertNotIn("&gt;", doc)

    def test_deterministic(self):
        self.assertEqual(render(sample())[0], render(sample())[0])

    def test_cli_default_and_output_paths(self):
        with tempfile.TemporaryDirectory() as d:
            md = Path(d) / "mr-1-x.md"
            md.write_text(sample(), encoding="utf-8")
            r = subprocess.run([sys.executable, str(SCRIPTS / "render_review.py"), str(md)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            a = (Path(d) / "mr-1-x.html").read_bytes()
            out = Path(d) / "other.html"
            subprocess.run([sys.executable, str(SCRIPTS / "render_review.py"), str(md), "-o", str(out)],
                           check=True)
            self.assertEqual(a, out.read_bytes())
            r = subprocess.run([sys.executable, str(SCRIPTS / "render_review.py"), str(Path(d) / "nope.md")],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("cannot read", r.stderr)

    def _run(self, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / "render_review.py"), *map(str, args)],
                              capture_output=True, text=True)

    def test_cli_refuses_to_overwrite_source(self):
        import hashlib
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            md = d / "a.md"
            md.write_text(sample(), encoding="utf-8")
            link = d / "link.html"
            link.symlink_to(md)
            other = d / "notes.html"
            other.write_text("hand written notes", encoding="utf-8")
            h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            before = h(md)
            for args in ([md, "-o", md], [md, "-o", d / "." / "a.md"], [md, "-o", link], [md, "-o", other]):
                r = self._run(*args)
                self.assertEqual(r.returncode, 1, args)
                self.assertIn("refusing", r.stderr)
                self.assertEqual(h(md), before)
            self.assertEqual(other.read_text(encoding="utf-8"), "hand written notes")
            # an .html input with default output (= itself) is refused and left untouched
            self.assertEqual(self._run(other).returncode, 1)
            self.assertEqual(other.read_text(encoding="utf-8"), "hand written notes")
            # re-rendering over a previously generated html is allowed
            self.assertEqual(self._run(md).returncode, 0)
            self.assertEqual(self._run(md).returncode, 0)

    def test_strengths_line_in_verdict(self):
        doc, warns = render(sample())
        self.assertEqual(warns, [])
        self.assertIn("Strengths: backoff is capped", doc)
        self.assertNotIn("unknown section", doc.lower())
        self.assertNotIn("Verdict not recognised", doc)
        # still detected as the verdict when the header has none
        md = sample().replace("**Verdict:** Request changes\n", "")
        doc2, _ = render(md)
        self.assertNotIn("Verdict not recognised", doc2)
        self.assertNotIn("Verdict unknown", doc2)

    def test_hostile_is_inert(self):
        doc, _ = render(HOSTILE)
        body = doc.split("</style>\n</head>")[1]
        self.assertNotRegex(body, r"<script|<img|<a |<b>|</style>")
        self.assertNotIn("<script", doc)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", body)
        self.assertIn("&lt;img src=x onerror=x&gt;", body)
        # the CSS is the only <style>, and nothing from the md closed it
        self.assertEqual(doc.count("</style>"), 1)
        # the fake verdict inside a finding body does not become the verdict
        self.assertIn("Request changes", doc.split('class="verdict ')[1].split("</section>")[0])
        self.assertNotIn("Verdict contradicts", doc)
        self.assertNotIn("Verdict mismatch", doc)
        self.assertNotRegex(body, r"<[^<>]*\bhref")
        self.assertNotRegex(body, r"=\s*[\"']?\s*javascript:")

    def test_malformed_card_banner(self):
        md = sample().replace("**Axis:** code", "**Axis:** nonsense")
        doc, warns = render(md)
        self.assertIn("1 of 2 cards parsed", doc)
        self.assertIn("<h2>Unparsed text</h2>", doc)
        self.assertIn("Retry loop never stops on 4xx", doc)  # kept, escaped
        self.assertTrue(any("unparsed" in w for w in warns))
        md = sample().replace("### [important]", "### [urgent]", 1)
        self.assertIn("1 of 2 cards parsed", render(md)[0])

    def test_contradictions(self):
        base = sample()
        d = render(base.replace("**Verdict:** Request changes", "**Verdict:** Approve", 1))[0]
        self.assertIn("Verdict contradicts findings", d)
        d = render(base.replace("**Verdict:** Request changes", "**Verdict:** Approve with changes", 1))[0]
        self.assertIn("Verdict contradicts findings", d)
        none = re.sub(r"### \[important\].*?(?=- \[nit\]|\n## )", "", base, flags=re.S)
        d = render(none)[0]
        self.assertIn("Verdict contradicts findings", d)
        self.assertNotIn("Verdict contradicts", render(base)[0])

    def test_odd_input_does_not_raise(self):
        for text in ("", "just text\n", "## Code findings\n### [minor]\n```\n"):
            doc, _ = render(text)
            self.assertIn("<main>", doc)


CARD_MD = """### [critical] Bad thing
**Axis:** code
**Confidence:** confirmed
**What:** broken
**Why:** because
**Fix:** fix it
"""


def review(findings="None.", verdict="Approve", extra="", code=None):
    """A conforming review whose Code findings section is `code` (default `findings`)."""
    return ("# Review: T\n**MR:** !1\n**Title:** t\n**Head SHA:** abc\n**Target:** main\n"
            "**Date:** 2026-10-04\n**Reviewers:** a\n**Verdict:** %s\n\n"
            "## Code findings\n%s\n\n## Business findings\nNone.\n\n"
            "## Process & convention findings\nNone.\n\n## Prior findings triaged\nNone.\n\n"
            "## Validation\nok\n%s\n## Verdict\n%s\n\nMost important fix first: x\n"
            % (verdict, findings if code is None else code, extra, verdict))


class DefectTests(unittest.TestCase):
    def test_findings_outside_known_sections_are_counted_and_bannered(self):
        md = review().replace("## Code findings\nNone.", "## Findings\n" + CARD_MD)
        doc, _ = render(md)
        self.assertIn("0 of 1 cards parsed", doc)
        self.assertIn("unknown section", doc)
        self.assertIn("missing section", doc)
        self.assertIn("### [critical] Bad thing", doc)  # shown escaped, not dropped
        self.assertIn("Verdict contradicts findings", doc)  # header says Approve
        self.assertNotIn("<p>No findings.</p>", doc)

    def test_case_variant_section_still_parsed_with_banner(self):
        md = review(code=CARD_MD).replace("## Code findings", "## Code Findings")
        doc, _ = render(md)
        self.assertEqual(doc.count("<article"), 1)
        self.assertIn("should be named", doc)
        self.assertNotIn("cards parsed", doc)

    def test_card_under_validation(self):
        doc, _ = render(review(extra=CARD_MD.replace("[critical]", "[important]")).replace("**Verdict:** Approve", "**Verdict:** Approve with changes", 1))
        self.assertIn("0 of 1 cards parsed", doc)
        self.assertIn("Verdict contradicts findings", doc)

    def test_critical_under_findings_with_approve(self):
        md = review(verdict="Approve").replace("## Code findings\nNone.", "## Findings\n" + CARD_MD)
        doc, _ = render(md)
        self.assertIn("cards parsed", doc)
        self.assertIn("Review file structure problems", doc)
        self.assertRegex(doc, r"Verdict contradicts findings")
        self.assertIn("NOT counted", doc)

    def test_not_a_structured_review(self):
        for text in ("", "\n\n", "just some prose\nmore\n", "\x00\x01garbage", "# Title only\n"):
            doc, _ = render(text)
            self.assertIn("Not a structured review — nothing was parsed", doc, repr(text))
            self.assertNotIn("No findings.", doc)
            self.assertNotIn("<table>", doc)
        self.assertIn("just some prose", render("just some prose\n")[0])

    def test_clean_review_has_no_banner(self):
        doc, warns = render(review())
        self.assertEqual(warns, [])
        self.assertNotIn("role=\"alert\"", doc)
        self.assertIn("No findings.", doc)

    def test_preamble_and_duplicate_header_rendered(self):
        md = review().replace("**MR:** !1\n", "**MR:** !1\nstray <b>preamble</b>\n**MR:** !2\n")
        doc, warns = render(md)
        self.assertIn("stray &lt;b&gt;preamble&lt;/b&gt;", doc)
        self.assertIn("**MR:** !2", doc)
        self.assertIn("Unparsed text", doc)
        self.assertIn("structure problems", doc)
        self.assertTrue(warns)

    def test_multiple_fences_in_suggested_change(self):
        card = CARD_MD.replace("[critical]", "[minor]") + (
            "**Suggested change:** first\n```\n-a\n+b\n```\nbetween\n```\n-c\n+d\n```\ntail\n")
        doc, _ = render(review(code=card, verdict="Approve"))
        for frag in ("-a", "+b", "-c", "+d"):
            self.assertIn(">%s</span>" % frag, doc)
        self.assertEqual(doc.count('class="diff"'), 2)
        self.assertLess(doc.index("first"), doc.index(">-a<"))
        self.assertLess(doc.index(">+b<"), doc.index("between"))
        self.assertLess(doc.index("between"), doc.index(">-c<"))
        self.assertLess(doc.index(">+d<"), doc.index("tail"))

    def test_no_patch_label_without_diff(self):
        card = CARD_MD.replace("[critical]", "[minor]") + "**Suggested change:** just words\n"
        doc, _ = render(review(code=card))
        self.assertIn("just words", doc)
        self.assertNotIn("Proposed patch", doc)
        card = CARD_MD.replace("[critical]", "[minor]") + "**Suggested change:** x\n```\n```\n"
        self.assertNotIn("Proposed patch", render(review(code=card))[0])

    def test_heading_inside_fence_is_not_a_card(self):
        card = CARD_MD.replace("[critical]", "[minor]").replace(
            "**Fix:** fix it", "**Fix:**\n```\n### [critical] fake\n```\n")
        doc, _ = render(review(code=card))
        self.assertNotIn("cards parsed", doc)
        self.assertEqual(rr.count_headings(card.split("\n"))[0], 1)
        self.assertEqual(rr.count_headings(["```", "### x", "```", "### y"])[0], 1)

    def test_unicode_line_separators_do_not_create_structure(self):
        for sep in ("\u2028", "\x85", "\x0b", "\x0c"):
            md = review(code=CARD_MD.replace("**What:** broken", "**What:** broken%s## Verdict%s### [nit] x" % (sep, sep)))
            doc, _ = render(md)
            self.assertNotIn("cards parsed", doc, repr(sep))
            self.assertEqual(doc.count("<article"), 1, repr(sep))
        doc, _ = render(review(code=CARD_MD, verdict="Request changes").replace("\n", "\r\n"))
        self.assertEqual(doc.count("<article"), 1)
        self.assertNotIn("role=\"alert\"", doc)
        doc, _ = render(review(code=CARD_MD, verdict="Request changes").replace("\n", "\r"))
        self.assertEqual(doc.count("<article"), 1)

    def test_nit_case_and_malformed_nit(self):
        doc, warns = render(review(code=CARD_MD + "- [Nit] odd case\n", verdict="Request changes"))
        self.assertIn("odd case", doc)
        self.assertNotIn("Review file structure problems", doc)
        self.assertTrue(any("case-insensitively" in w for w in warns))
        doc, warns = render(review(code=CARD_MD + "- [nit]\n", verdict="Request changes"))
        self.assertIn("malformed nit line", doc)
        self.assertIn("structure problems", doc)
        self.assertTrue(warns)

    def test_bullet_in_card_field_does_not_cut_card(self):
        card = CARD_MD.replace("**Fix:** fix it", "**Fix:**\n- [ ] first step\n- [docs](x) read this\n- [NIT] real nit")
        doc, warns = render(review(code=card, verdict="Request changes"))
        art = doc.split("<article")[1].split("</article>")[0]
        self.assertIn("[ ] first step", art)
        self.assertIn("[docs](x) read this", art)
        self.assertNotIn("real nit", art)  # a case-insensitive nit is still a boundary
        self.assertIn("real nit", doc)
        self.assertNotIn("cards parsed", doc)
        self.assertNotIn("Review file structure problems", doc)
        # with no open card, a stray `- [` bullet is flagged, not silently dropped
        doc, _ = render(review(code="- [x] other\n" + CARD_MD, verdict="Request changes"))
        self.assertIn("- [x] other", doc)
        self.assertIn("malformed nit line", doc)

    def test_plain_headings_in_non_findings_sections_are_not_cards(self):
        md = review().replace("## Validation\nok\n", "## Validation\n### Tests\nok\n### Lint\nok\n")
        md = md.replace("## Prior findings triaged\nNone.", "## Prior findings triaged\n### Earlier thread\nfixed")
        doc, _ = render(md)
        self.assertNotIn("cards parsed", doc)
        self.assertEqual(rr.count_headings(["## Validation", "### Tests", "### [minor] x"])[0], 1)
        # inside findings sections and unknown sections every ### still counts
        self.assertEqual(rr.count_headings(["## Code findings", "### plain"])[0], 1)
        self.assertEqual(rr.count_headings(["## Mystery", "### plain"])[0], 1)
        self.assertIn("1 of 1 cards parsed".replace("1 of 1", "0 of 1"),
                      render(review(code="### plain heading\ntext"))[0])

    def test_bold_most_important_fix_first(self):
        md = review().replace("Most important fix first: x", "**Most important fix first:** do the thing")
        doc, warns = render(md)
        self.assertIn("do the thing", doc)
        self.assertNotIn("No most-important-fix line found", doc)
        self.assertFalse(any("lacks" in w for w in warns))

    def test_deterministic_across_hash_seeds(self):
        md = HOSTILE + "\n## Extra\n" + CARD_MD + "\n## Another\nx\n"
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "r.md"
            f.write_text(md, encoding="utf-8")
            outs = []
            for seed in ("1", "2"):
                o = Path(d) / ("o%s.html" % seed)
                r = subprocess.run([sys.executable, str(SCRIPTS / "render_review.py"), str(f), "-o", str(o)],
                                   capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED=seed))
                self.assertEqual(r.returncode, 0, r.stderr)
                outs.append((o.read_bytes(), r.stderr))
            self.assertEqual(outs[0], outs[1])


# The report-format.md sample as it was before the v2 fields (Mode, ID, In diff, ...) existed, and the
# sha256 of its html from the renderer of that time. An old-format md must keep rendering byte-identically;
# change OLD_SAMPLE_SHA256 only for a deliberate change to the html output.
OLD_SAMPLE = """# Review: Add retry backoff to sync client
**MR:** !123
**Title:** Add retry backoff to sync client
**Head SHA:** 4f2a9c1
**Target:** main
**Date:** 2026-10-04
**Reviewers:** Cass (code), Sol (business)
**Verdict:** Request changes

## Code findings
### [important] Retry loop never stops on 4xx
**Axis:** code
**Anchor:** acme-sync/sync/client/retry.py:42
**Confidence:** confirmed
**What:** A permanent 400 is retried forever, hammering the API.
**Why:** `while True: resp = send(req)  # no status check`
**Fix:** Stop on non-retryable status codes and cap attempts.
**Suggested change:**
Proposed patch (not posted)
```diff
-while True:
+for _ in range(MAX_ATTEMPTS):
```
- [nit] Rename `d` to `delay`. (`acme-sync/sync/client/retry.py:50`)

## Business findings
### [minor] No user-visible failure state
**Axis:** business
**Confidence:** suspected
**What:** Is the user told when retries are exhausted?
**Why:** AC-3 requires an error toast; the diff adds none.
**Fix:** Surface the final failure, or confirm AC-3 is out of scope.

## Process & convention findings
None.

## Prior findings triaged
- Refuted: bot "SQL injection" at db.py:9 — the query is parameterised.

## Validation
- `pytest tests/sync` — pass. CI green on 4f2a9c1.

## Verdict
Strengths: backoff is capped and jittered; the new tests cover the 5xx path.
Request changes
Most important fix first: stop retrying non-retryable 4xx responses.
"""
# To regenerate a pin, run the *previous* renderer (e.g. `git show <old rev>:scripts/render_review.py`)
# on the old fixture. Never paste the current output's hash: that would pin whatever it renders now.
OLD_SAMPLE_SHA256 = "7678682635b9ec5dd900d30df9fdd611bfd8b30412e7f2593bd90cd4cce12e06"
# The same rule: the html of OLD_F5_NITS from the renderer before v2 (nit text kept verbatim).
OLD_F5_NITS = review(code=CARD_MD + "- [nit] F5 reloads the page twice.\n- [nit] F5 again here.\n",
                     verdict="Request changes")
OLD_F5_NITS_SHA256 = "1bdd850e45051193a5012a605d14a026d7fb19fa6a1669fbea60114d853aba6a"

V2_CARD = """### [critical] Bad thing
**ID:** F3
**Axis:** code
**Anchor:** repo/a.py:1
**Confidence:** confirmed
**What:** broken
**Why:** because
**Fix:** fix it
**Carried:** from 1a2b3c4
**In diff:** yes
**Marker:** 0123456789ab
**Posted:** github review comment 987 @ 1a2b3c4
"""


def v2_review(card=V2_CARD, nits="- [nit] F4 Rename `d` to `delay`. (`repo/a.py:2`)\n", header=None):
    hdr = "**Mode:** since-last\n**Since:** 1a2b3c4\n**Ticket:** ABC-12 (fetched)\n" if header is None else header
    return review(code=card + nits, verdict="Request changes").replace(
        "**Verdict:** Request changes\n\n", "**Verdict:** Request changes\n" + hdr + "\n", 1)


class V2FieldTests(unittest.TestCase):
    def test_old_format_renders_unchanged(self):
        import hashlib
        doc, warns = render(OLD_SAMPLE)
        self.assertEqual(warns, [])
        self.assertEqual(hashlib.sha256(doc.encode("utf-8")).hexdigest(), OLD_SAMPLE_SHA256)

    def test_new_format_renders_clean_with_all_fields_shown(self):
        doc, warns = render(v2_review())
        self.assertEqual(warns, [])
        self.assertNotIn('role="alert"', doc)
        for k, v in (("Mode", "since-last"), ("Since", "<code>1a2b3c4</code>"), ("Ticket", "ABC-12 (fetched)")):
            self.assertIn("<dt>%s</dt><dd>%s</dd>" % (k, v), doc)
        meta = doc.split('<p class="f-meta">')[1].split("</p>")[0]
        self.assertIn('<span class="tag">F3</span>', meta)
        self.assertIn('<span class="tag">In diff: yes</span>', meta)
        rows = doc.split('<dl class="rows">')[1].split("</dl>")[0]
        self.assertNotIn("<dt>ID</dt>", rows)
        self.assertNotIn("<dt>In diff</dt>", rows)
        for k, v in (("Carried", "from 1a2b3c4"), ("Marker", "0123456789ab"),
                     ("Posted", "github review comment 987 @ 1a2b3c4")):
            self.assertIn("<dt>%s</dt><dd><p>%s</p></dd>" % (k, v), rows)
        nit = doc.split('<ul class="nits">')[1].split("</ul>")[0]
        self.assertIn("<code>F4</code> Rename <code>d</code> to", nit)
        self.assertEqual(render(v2_review())[0], doc)

    def test_header_keys_are_optional_and_partial_sets_are_fine(self):
        for hdr in ("", "**Mode:** fresh\n", "**Mode:** full\n", "**Since:** " + "a" * 40 + "\n",
                    "**Ticket:** KEY-1 (not fetched: no Jira skill/tool available)\n"):
            doc, warns = render(v2_review(header=hdr))
            self.assertEqual(warns, [], hdr)
            self.assertNotIn('role="alert"', doc)

    def test_bad_mode_since_in_diff_warn_with_banner(self):
        cases = (
            (v2_review(header="**Mode:** Fresh\n"), "Mode"),
            (v2_review(header="**Mode:** since <sha>\n"), "Mode"),
            (v2_review(header="**Since:** 1A2B3C4\n"), "Since"),
            (v2_review(header="**Since:** abc12\n"), "Since"),
            (v2_review(card=V2_CARD.replace("**In diff:** yes", "**In diff:** maybe")), "In diff"),
        )
        for md, key in cases:
            doc, warns = render(md)
            self.assertTrue(any(key in w for w in warns), (key, warns))
            self.assertIn("Review file structure problems", doc)
        doc, _ = render(cases[-1][0])
        self.assertIn('<span class="tag">In diff: maybe</span>', doc)  # still shown, escaped

    def test_duplicate_ids_warn_across_cards_and_nits(self):
        biz = V2_CARD.replace("[critical]", "[minor]").replace("**Axis:** code", "**Axis:** business")
        md = v2_review(nits="- [nit] F3 Same id as the card.\n").replace(
            "## Business findings\nNone.", "## Business findings\n" + biz)
        doc, warns = render(md)
        dup = [w for w in warns if "duplicate ID" in w]
        self.assertEqual(len(dup), 1, warns)
        self.assertIn("F3", dup[0])
        self.assertIn("duplicate ID", doc)
        self.assertIn("Review file structure problems", doc)
        self.assertEqual(doc.count("<article"), 2)  # both cards still render

    def test_bad_card_ids_warn(self):
        for bad in ("banana", "F1\nF2", "F03", "F0", "f1"):
            md = v2_review(card=V2_CARD.replace("**ID:** F3", "**ID:** " + bad))
            doc, warns = render(md)
            self.assertTrue(any("ID" in w and "F<n>" in w for w in warns), (bad, warns))
            self.assertIn("Review file structure problems", doc)

    def test_ids_compare_by_number(self):
        md = v2_review(nits="- [nit] F03 Same number as the card.\n")
        warns = render(md)[1]
        self.assertEqual(len([w for w in warns if "duplicate ID" in w]), 1, warns)
        biz = V2_CARD.replace("[critical]", "[minor]").replace("**Axis:** code", "**Axis:** business") \
            .replace("**ID:** F3", "**ID:** F03")
        md = v2_review(nits="").replace("## Business findings\nNone.", "## Business findings\n" + biz)
        self.assertEqual(len([w for w in render(md)[1] if "duplicate ID" in w]), 1)

    def test_nit_prefix_is_not_an_id_in_a_file_without_card_ids(self):
        import hashlib
        doc, warns = render(OLD_F5_NITS)
        self.assertEqual(warns, [])
        self.assertNotIn('role="alert"', doc)
        self.assertIn("<span>F5 reloads the page twice.</span>", doc)
        self.assertEqual(hashlib.sha256(doc.encode("utf-8")).hexdigest(), OLD_F5_NITS_SHA256)

    def test_no_ids_means_no_new_warnings(self):
        doc, warns = render(review(code=CARD_MD + "- [nit] F is not an id here\n", verdict="Request changes"))
        self.assertEqual(warns, [])
        self.assertIn("<span>F is not an id here</span>", doc)

    def test_ticket_line_shown_in_masthead(self):
        hdr = "**Ticket:** ABC-12 (fetched), ABC-13 (not fetched: no Jira skill/tool available)\n"
        doc, warns = render(v2_review(header=hdr))
        self.assertEqual(warns, [])
        self.assertIn("<dt>Ticket</dt><dd>ABC-12 (fetched), ABC-13 (not fetched: no Jira skill/tool "
                      "available)</dd>", doc)

    def test_ticket_state_warning_is_soft_and_lenient(self):
        # One key with a state is enough; "fetched via <tool>" counts.
        for ok in ("ABC-12 (fetched)", "ABC-12 (fetched via the session's Jira tool)",
                   "ABC-12 (not fetched: tool not authorised)", "ABC-12, ABC-13 (fetched)",
                   "ABC-12 (Fetched)", "ABC-12 (not fetched: not found or not visible)"):
            doc, warns = render(v2_review(header="**Ticket:** %s\n" % ok))
            self.assertEqual(warns, [], ok)
        # No state for any key: a hand-written header. Warned on stderr, no banner, still shown.
        for bad in ("ABC-12", "ABC-12, ABC-13", "ABC-12 (done)", "ABC-12 fetched", "ABC-12 (prefetched)"):
            doc, warns = render(v2_review(header="**Ticket:** %s\n" % bad))
            self.assertEqual(len(warns), 1, (bad, warns))
            self.assertIn("Ticket", warns[0])
            self.assertIn("(fetched", warns[0])
            self.assertNotIn('role="alert"', doc)
            self.assertIn("<dt>Ticket</dt><dd>%s</dd>" % bad, doc)

    def test_sample_carries_ticket_and_quoted_ac(self):
        s = sample()
        self.assertRegex(s, r"\n\*\*Ticket:\*\* [A-Z]+-\d+ \(fetched")
        why = [l for l in s.splitlines() if l.startswith("**Why:** `") and " AC-" in l]
        self.assertEqual(len(why), 1, why)
        self.assertRegex(why[0], r"^\*\*Why:\*\* `[A-Z]+-\d+ AC-\d+: [^`]+`$")
        self.assertIn("<dt>Ticket</dt>", render(s)[0])
        self.assertIn("fetched via the session's Jira tool", s)
        card = s.split("### [important] No user-visible failure state\n")[1].split("\n\n")[0]
        self.assertIn("**Confidence:** suspected", card)
        what = re.search(r"^\*\*What:\*\* (.*)$", card, re.M).group(1)
        self.assertIn("?", what)
        for k in ("What", "Fix"):  # posted as-is, so ticket-free already in the md
            v = re.search(r"^\*\*%s:\*\* (.*)$" % k, card, re.M).group(1)
            self.assertNotRegex(v, r"[A-Z][A-Z0-9]+-\d+|\bAC\b|ticket", k)

    def test_ticket_state_after_a_source(self):
        for ok in ("ABC-12 (branch, fetched via the session's Jira tool)",
                   "ABC-12 (title, not fetched: tool not authorised)"):
            self.assertEqual(render(v2_review(header="**Ticket:** %s\n" % ok))[1], [], ok)

    def test_ac_quote_with_backtick_replaced_keeps_one_code_span(self):
        # A backtick inside the quoted AC is written as ' so the inline code span holds.
        card = V2_CARD.replace("**Why:** because", "**Why:** `ABC-12 AC-2: running 'make test' passes`")
        doc, warns = render(v2_review(card=card))
        self.assertEqual(warns, [])
        why = doc.split("<dt>Why</dt><dd>")[1].split("</dd>")[0]
        self.assertEqual(why.count("<code>"), 1, why)
        self.assertNotIn("`", why)

    def test_v2_fields_are_escaped(self):
        card = V2_CARD.replace("F3", "<b>F3</b>").replace("yes", "<i>yes</i>").replace(
            "0123456789ab", "<script>x</script>")
        md = v2_review(card=card, header="**Mode:** <img>\n**Ticket:** <a href=x>K-1</a>\n")
        body = render(md)[0].split("</style>\n</head>")[1]
        self.assertNotRegex(body, r"<script|<img|<a |<b>|<i>")


VERIFY_OK = "- Verify: 4 found, 2 kept, 1 downgraded, 1 dropped (Cass refute round; trigger: ≥1 important)\n"


class VerifyLineTests(unittest.TestCase):
    def verify_warns(self, extra):
        doc, warns = render(review(extra=extra))
        return doc, [w for w in warns if "Verify" in w]

    def test_good_sum_renders_clean(self):
        for line in (VERIFY_OK,
                     "- Verify: 0 found, 0 kept, 0 downgraded, 0 dropped (Maestro re-read; trigger: none)\n",
                     "- Verify: 2 found, 2 kept, 0 downgraded, 0 dropped (Maestro re-read (no subagent on this "
                     "install); trigger: >8 non-nit)\n"):
            doc, warns = render(review(extra=line))
            self.assertEqual(warns, [], line)
            self.assertNotIn('role="alert"', doc)

    def test_bad_sum_warns_with_banner(self):
        doc, warns = self.verify_warns(VERIFY_OK.replace("4 found", "5 found"))
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("5 found", warns[0])
        self.assertIn("2+1+1", warns[0])
        self.assertIn("Review file structure problems", doc)

    def test_duplicate_line_warns_with_banner(self):
        doc, warns = self.verify_warns(VERIFY_OK + VERIFY_OK)
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("2 times", warns[0])
        self.assertIn("Review file structure problems", doc)

    def test_malformed_line_warns(self):
        for bad in ("- Verify: 4 found, 2 kept, 1 downgraded (Maestro re-read)\n",
                    "- Verify: 4 found, 2 kept, 1 downgraded, 1 dropped\n",
                    "- Verify: four found, 2 kept, 1 downgraded, 1 dropped (Maestro re-read)\n"):
            doc, warns = self.verify_warns(bad)
            self.assertEqual(len(warns), 1, (bad, warns))
            self.assertIn("malformed", warns[0])
            self.assertIn("Review file structure problems", doc)

    def test_bold_and_lowercase_forms_are_checked(self):
        bold = VERIFY_OK.replace("- Verify:", "- **Verify:**")
        lower = VERIFY_OK.replace("- Verify:", "- verify:")
        for line in (bold, lower, "* " + VERIFY_OK[2:]):
            self.assertEqual(render(review(extra=line))[1], [], line)
        for line in (bold.replace("4 found", "5 found"), lower.replace("4 found", "5 found")):
            doc, warns = self.verify_warns(line)
            self.assertEqual(len(warns), 1, (line, warns))
            self.assertIn("2+1+1", warns[0])
        doc, warns = self.verify_warns(VERIFY_OK + bold)
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("2 times", warns[0])
        for bad in ("- **Verify:** four found\n", VERIFY_OK.replace("- Verify:", "- **Verify**:")):
            doc, warns = self.verify_warns(bad)
            self.assertEqual(len(warns), 1, (bad, warns))
            self.assertIn("malformed", warns[0])
        self.assertIn("Review file structure problems", doc)

    def test_missing_line_and_other_verify_text_are_fine(self):
        for extra in ("", "- Verify Suggested change F1: dropped, lines differ\n", "- verified CI\n",
                      "- Suggested change dropped F1: lines differ\n"):
            self.assertEqual(render(review(extra=extra))[1], [], extra)

    def test_only_the_validation_section_is_read(self):
        md = review(extra="").replace("## Prior findings triaged\nNone.",
                                      "## Prior findings triaged\n" + VERIFY_OK.replace("4 found", "9 found"))
        self.assertEqual(render(md)[1], [])

    def test_evidence_part_is_accepted(self):
        line = VERIFY_OK.replace("≥1 important)", "≥1 important; evidence: 2/3 tagged)")
        doc, warns = render(review(extra=line))
        self.assertEqual(warns, [], line)
        self.assertNotIn("Review file structure problems", doc)

    def test_malformed_evidence_part_warns(self):
        for ev in ("x/y tagged", "5/3 tagged", ""):
            line = VERIFY_OK.replace("≥1 important)", "≥1 important; evidence: %s)" % ev)
            warns = render(review(extra=line))[1]
            self.assertTrue(any("malformed Verify evidence" in w for w in warns), (ev, warns))

    def test_sample_carries_a_valid_verify_line(self):
        self.assertEqual(len(re.findall(r"^- Verify: ", sample(), re.M)), 1)
        self.assertEqual(render(sample())[1], [])


def anchor_review(anchor):
    return review(code=CARD_MD.replace("**Confidence:**", "**Anchor:** %s\n**Confidence:**" % anchor, 1),
                  verdict="Request changes")


class AnchorTests(unittest.TestCase):
    GOOD = {
        "repo/a.py:7": ("repo/a.py", "new", 7, 7),
        "repo/a.py:3-9": ("repo/a.py", "new", 3, 9),
        "repo/a.py:-7": ("repo/a.py", "old", 7, 7),
        "repo/a.py:-3-9": ("repo/a.py", "old", 3, 9),
        "repo/a.py (deleted)": ("repo/a.py", "file", None, None),
        "repo/src/v2-api/x-1.py:10-12": ("repo/src/v2-api/x-1.py", "new", 10, 12),
        "repo/src/v2-api/x-1.py:-10-12": ("repo/src/v2-api/x-1.py", "old", 10, 12),
        "repo/a:b.py:4": ("repo/a:b.py", "new", 4, 4),
        "repo/my dir/a b.py:4-4": ("repo/my dir/a b.py", "new", 4, 4),
        "`repo/a.py:5`": ("repo/a.py", "new", 5, 5),
    }
    BAD = ("repo/a.py:", "repo/a.py:abc", "repo/a.py:3-", "repo/a.py:-", "repo/a.py", "repo/a.py:0",
           "repo/a.py:3--5", "repo/a.py:-3-+5", "repo/a.py:3, repo/b.py:5", ":3", "repo/a.py:1.5",
           "repo/a.py:L3", " (deleted)", "repo/a.py:3, repo/b.py (deleted)", "/abs/a.py:3",
           "/abs/a.py (deleted)", "repo/a`b.py:3", "repo/a`b.py (deleted)")

    def test_parse_good_forms(self):
        for text, want in self.GOOD.items():
            a = rr.parse_anchor(text)
            self.assertIsNotNone(a, text)
            self.assertEqual((a["path"], a["side"], a["start"], a["end"]), want, text)

    def test_parse_malformed(self):
        for text in self.BAD:
            self.assertIsNone(rr.parse_anchor(text), text)

    def test_good_anchors_render_clean(self):
        for text in self.GOOD:
            doc, warns = render(anchor_review(text))
            self.assertEqual(warns, [], text)
            self.assertNotIn('role="alert"', doc)
            self.assertIn('<code class="anchor">%s</code>' % rr.e(text.strip("`")), doc)

    def test_malformed_anchor_warns_with_banner(self):
        for text in self.BAD:
            doc, warns = render(anchor_review(text))
            self.assertTrue(any("Anchor" in w and "malformed" in w for w in warns), (text, warns))
            self.assertIn("Review file structure problems", doc)
            self.assertEqual(doc.count("<article"), 1)  # the card still renders

    def test_reversed_range_warns(self):
        for text in ("repo/a.py:9-3", "repo/a.py:-9-3"):
            doc, warns = render(anchor_review(text))
            self.assertTrue(any("Anchor" in w and "reversed" in w for w in warns), (text, warns))
            self.assertIn("Review file structure problems", doc)
        self.assertIsNotNone(rr.parse_anchor("repo/a.py:9-3"))  # parsed, then flagged

    def test_anchor_is_optional(self):
        doc, warns = render(review(code=CARD_MD, verdict="Request changes"))
        self.assertEqual(warns, [])
        self.assertNotIn("anchor", doc.split("</style>")[1])

    def test_nit_anchor_is_not_validated(self):
        md = review(code=CARD_MD + "- [nit] Odd. (`repo/a.py:9-3`)\n- [nit] Odd. (`repo/a.py:`)\n",
                    verdict="Request changes")
        self.assertEqual(render(md)[1], [])


DIFF = """diff --git a/src/v2-api/x-1.py b/src/v2-api/x-1.py
index 1..2 100644
--- a/src/v2-api/x-1.py
+++ b/src/v2-api/x-1.py
@@ -10,3 +10,4 @@ def f():
@@ -20 +21,0 @@
@@ -30,0 +31,2 @@
diff --git a/old name.py b/new name.py
--- a/old name.py\t
+++ b/new name.py\t
@@ -5,2 +5,2 @@
diff --git a/gone.py b/gone.py
deleted file mode 100644
--- a/gone.py
+++ /dev/null
@@ -1,3 +0,0 @@
diff --git "a/q\\"t.py" "b/q\\"t.py"
--- "a/q\\"t.py"
+++ "b/q\\"t.py"
@@ -1 +1 @@
"""


class InDiffTests(unittest.TestCase):
    def check(self, anchor, want):
        self.assertEqual(rr.anchor_in_diff(DIFF, anchor), want, anchor)

    def test_new_side(self):
        for a in ("r/src/v2-api/x-1.py:10", "r/src/v2-api/x-1.py:10-13", "r/src/v2-api/x-1.py:31-32",
                  "src/v2-api/x-1.py:13"):
            self.check(a, "yes")
        for a in ("r/src/v2-api/x-1.py:9", "r/src/v2-api/x-1.py:14", "r/src/v2-api/x-1.py:13-31",
                  "r/src/v2-api/x-1.py:21", "r/src/v2-api/x-1.py:30-31"):
            self.check(a, "no")
        self.check("r/other.py:10", "nofile")

    def test_old_side(self):
        for a in ("r/src/v2-api/x-1.py:-10-12", "r/src/v2-api/x-1.py:-20", "r/gone.py:-1-3"):
            self.check(a, "yes")
        for a in ("r/src/v2-api/x-1.py:-13", "r/src/v2-api/x-1.py:-30", "r/src/v2-api/x-1.py:-12-20",
                  "r/gone.py:-4"):
            self.check(a, "no")

    def test_renames_use_the_new_path_on_both_sides(self):
        self.check("r/new name.py:5-6", "yes")
        self.check("r/new name.py:-6", "yes")   # old side of a renamed file: mapped to its --- path
        self.check("r/old name.py:-6", "nofile")  # the old name is never the anchor path
        self.check("r/old name.py:5", "nofile")
        self.check('r/q"t.py:1', "yes")

    def test_deleted_file_uses_its_old_path(self):
        self.check("r/gone.py:-2", "yes")

    def test_header_state_is_per_file(self):
        diff = ("diff --git a/q.sql b/q.sql\n--- a/q.sql\n+++ b/q.sql\n@@ -2 +1,0 @@\n"
                "--- a comment\n@@ -4 +3 @@\n-x\n+y\n"
                "diff --git a/p.txt b/p.txt\n--- a/p.txt\n+++ b/p.txt\n@@ -9,0 +10 @@\n"
                "+++ c\n@@ -17 +18 @@\n-o\n+n\n"
                "diff --git a/img.png b/img.png\nBinary files a/img.png and b/img.png differ\n"
                "diff --git a/m.sh b/m.sh\nold mode 100644\nnew mode 100755\n"
                "diff --git a/r1.py b/r2.py\nsimilarity index 100%\nrename from r1.py\nrename to r2.py\n")
        for a, want in (("r/q.sql:-4", "yes"), ("r/q.sql:3", "yes"), ("r/p.txt:18", "yes"),
                        ("r/p.txt:-17", "yes"), ("r/img.png:1", "nofile"), ("r/m.sh:1", "nofile"),
                        ("r/r2.py:1", "nofile"), ("r/r2.py:-1", "nofile")):
            self.assertEqual(rr.anchor_in_diff(diff, a), want, a)

    def test_quoted_non_ascii_paths(self):
        diff = ('diff --git "a/\u4e2d\\"q.py" "b/\u4e2d\\"q.py"\n--- "a/\u4e2d\\"q.py"\n'
                '+++ "b/\u4e2d\\"q.py"\n@@ -1 +1 @@\n'
                'diff --git "a/\\303\\274.py" "b/\\303\\274.py"\n--- "a/\\303\\274.py"\n'
                '+++ "b/\\303\\274.py"\n@@ -1 +1,2 @@\n')
        self.assertEqual(rr.anchor_in_diff(diff, 'r/\u4e2d"q.py:1'), "yes")
        self.assertEqual(rr.anchor_in_diff(diff, "r/\u00fc.py:2"), "yes")

    def test_repo_prefix_matches_only_the_exact_path(self):
        diff = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n"
        self.assertEqual(rr.anchor_in_diff(diff, "src/x.py:1"), "yes")  # no --repo: first segment dropped
        self.assertEqual(rr.anchor_in_diff(diff, "src/x.py:1", repo="acme"), "nofile")
        self.assertEqual(rr.anchor_in_diff(diff, "acme/x.py:1", repo="acme"), "yes")
        self.assertEqual(rr.anchor_in_diff(diff, "x.py:1", repo="acme"), "yes")
        self.assertEqual(rr.anchor_in_diff(diff, "other/x.py:1", repo="acme"), "nofile")
        self.assertEqual(rr.anchor_in_diff(diff, "x.py:5", repo="acme"), "no")  # file found, line not

    def test_file_level_reversed_and_malformed(self):
        self.check("r/gone.py (deleted)", "no")
        self.check("r/src/v2-api/x-1.py:12-10", None)
        self.check("r/src/v2-api/x-1.py:", None)


class InDiffCliTests(unittest.TestCase):
    def run_cli(self, md, diff, *extra):
        with tempfile.TemporaryDirectory() as d:
            src, dp = Path(d) / "review.md", Path(d) / "pr.diff"
            src.write_text(md, encoding="utf-8")
            dp.write_text(diff, encoding="utf-8")
            r = subprocess.run([sys.executable, str(SCRIPTS / "render_review.py"), "--in-diff", str(dp)]
                               + list(extra) + [str(src)], capture_output=True, text=True,
                               env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            return r, sorted(p.name for p in Path(d).iterdir())

    def test_prints_one_line_per_anchored_card_and_writes_nothing(self):
        cards = (V2_CARD.replace("repo/a.py:1", "acme/a.py:2-3")
                 + CARD_MD.replace("Bad thing", "No id\there").replace(
                     "**Confidence:**", "**Anchor:** acme/a.py:9-3\n**Confidence:**")
                 + CARD_MD.replace("Bad thing", "Plain"))  # no Anchor: no line
        biz = V2_CARD.replace("[critical]", "[minor]").replace("**Axis:** code", "**Axis:** business") \
            .replace("F3", "F7").replace("repo/a.py:1", "acme/a.py (deleted)")
        md = v2_review(card=cards, nits="").replace("## Business findings\nNone.", "## Business findings\n" + biz)
        diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -2 +2,2 @@\n"
        r, files = self.run_cli(md, diff, "--repo", "acme")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "F3\tacme/a.py:2-3\tyes\nNo id here\tacme/a.py:9-3\tmalformed\n"
                                   "F7\tacme/a.py (deleted)\tno\n")
        self.assertEqual(files, ["pr.diff", "review.md"])  # no html written

    def test_nofile_for_wrong_repo_and_old_name_on_rename(self):
        cards = (V2_CARD.replace("repo/a.py:1", "acme/a.py:2")
                 + V2_CARD.replace("F3", "F4").replace("repo/a.py:1", "acme/old.py:-1"))
        diff = ("diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -2 +2 @@\n"
                "diff --git a/old.py b/new.py\n--- a/old.py\n+++ b/new.py\n@@ -1 +1 @@\n")
        r, _ = self.run_cli(v2_review(card=cards, nits=""), diff, "--repo", "wrong")
        self.assertEqual(r.stdout, "F3\tacme/a.py:2\tnofile\nF4\tacme/old.py:-1\tnofile\n")
        r, _ = self.run_cli(v2_review(card=cards, nits=""), diff, "--repo", "acme")
        self.assertEqual(r.stdout, "F3\tacme/a.py:2\tyes\nF4\tacme/old.py:-1\tnofile\n")

    def test_unreadable_diff_fails(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "review.md"
            src.write_text(v2_review(), encoding="utf-8")
            r = subprocess.run([sys.executable, str(SCRIPTS / "render_review.py"), "--in-diff",
                                str(Path(d) / "missing.diff"), str(src)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "")


class PostedFieldTests(unittest.TestCase):
    def test_good_marker_and_posted_forms_render_clean(self):
        for posted in ("github review comment 987 @ 1a2b3c4", "https://github.com/o/r/pull/1#discussion_r55 @ 1a2b3c4",
                       "!123#note_881 @ 4f2a9c1", "discussion 8f3e @ " + "a" * 40):
            doc, warns = render(v2_review(card=V2_CARD.replace("github review comment 987 @ 1a2b3c4", posted)))
            self.assertEqual(warns, [], posted)
            self.assertNotIn('role="alert"', doc)

    def test_malformed_marker_warns_with_banner(self):
        for bad in ("0123456789AB", "0123456789a", "0123456789abc", "bq:0123456789ab", "zzzzzzzzzzzz"):
            doc, warns = render(v2_review(card=V2_CARD.replace("0123456789ab", bad)))
            self.assertTrue(any("Marker" in w for w in warns), (bad, warns))
            self.assertIn("Review file structure problems", doc)

    def test_malformed_posted_warns_with_banner(self):
        for bad in ("github review comment 987", "987 @1a2b3c4", "987 @ 1A2B3C4", "987 @ abc12", "@ 1a2b3c4"):
            doc, warns = render(v2_review(card=V2_CARD.replace("github review comment 987 @ 1a2b3c4", bad)))
            self.assertTrue(any("Posted" in w for w in warns), (bad, warns))
            self.assertIn("Review file structure problems", doc)

    def test_triage_and_nit_tails_are_checked(self):
        good = ("- Not re-raised: F5 — Old thing (Marker aaaaaaaaaaaa, Posted !1#note_2 @ 1a2b3c4)\n"
                "- Fixed: F6 — `return x` (Posted !1#note_3 @ 1a2b3c4)\n- Fixed: F7 — `ok`\n")
        md = v2_review().replace("## Prior findings triaged\nNone.", "## Prior findings triaged\n" + good)
        self.assertEqual(render(md)[1], [])
        for bad in ("- Fixed: F6 — `x` (Marker AAA, Posted !1#note_3 @ 1a2b3c4)\n",
                    "- Not re-raised: F6 — y (Posted !1#note_3)\n"):
            md = v2_review().replace("## Prior findings triaged\nNone.", "## Prior findings triaged\n" + bad)
            warns = render(md)[1]
            self.assertEqual(len(warns), 1, (bad, warns))
        warns = render(v2_review(nits="- [nit] F4 Rename. (`repo/a.py:2`) (Marker 123, Posted x @ 1a2b3c4)\n"))[1]
        self.assertTrue(any("Marker" in w for w in warns), warns)

    def test_marker_helper(self):
        self.assertEqual(rr.marker("mr-123", "canonical", "F1"), "2a85e007323e")
        self.assertEqual(rr.marker("mr-123", "fresh-4f2a9c1", "F2"), "c2e9b2b6748d")
        self.assertEqual(len(rr.marker("branch-feat-x", "canonical", "F1")), 12)  # a slugged branch key
        for bad in (("mr-123", "fresh", "F1"), ("mr-123", "fresh-4F2A9C1", "F1"), ("mr-123", "canonical", "1"),
                    ("", "canonical", "F1"), ("a|b", "canonical", "F1"), ("MR-123", "canonical", "F1"),
                    ("feat/x", "canonical", "F1"), ("branch-feat/x", "canonical", "F1"), ("a" * 65, "canonical", "F1")):
            with self.assertRaises(ValueError, msg=bad):
                rr.marker(*bad)
        r = subprocess.run([sys.executable, str(SCRIPTS / "render_review.py"), "--marker", "mr-123", "canonical", "F1"],
                           capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual((r.returncode, r.stdout), (0, "2a85e007323e\n"), r.stderr)
        r = subprocess.run([sys.executable, str(SCRIPTS / "render_review.py"), "--marker", "mr-123", "fresh", "F1"],
                           capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")


class NearMissTests(unittest.TestCase):
    def triage_warns(self, line):
        md = v2_review().replace("## Prior findings triaged\nNone.", "## Prior findings triaged\n" + line)
        doc, warns = render(md)
        return doc, warns

    def test_trailing_period_or_semicolon_after_tail_is_fine(self):
        for end in (".", ";", ". "):
            line = "- Fixed: F6 — `x` (Marker aaaaaaaaaaaa, Posted !1#note_3 @ 1a2b3c4)%s\n" % end
            self.assertEqual(self.triage_warns(line)[1], [], end)
        self.assertEqual(rr.parse_tail("x (Marker aaaaaaaaaaaa)."), ("aaaaaaaaaaaa", None, None))

    def test_near_miss_tails_warn(self):
        for bad in ("- Fixed: F6 — `x` (Marker: aaaaaaaaaaaa)\n",
                    "- Fixed: F6 — `x` (marker aaaaaaaaaaaa, posted !1 @ 1a2b3c4)\n",
                    "- Fixed: F6 — `x` (Marker aaaaaaaaaaaa) see thread\n",
                    "- Fixed: F6 — `x` (Marker aaaaaaaaaaaa, Posted note(3) @ 1a2b3c4)\n",
                    "- Fixed: F6 — `x` (Posted !1#note_3 @ 1a2b3c4, Marker aaaaaaaaaaaa)\n",
                    "- **Not re-raised:** F2 — Old thing (Marker aaaaaaaaaaaa)\n",
                    "- **Fixed**: F2 — `x`\n"):
            doc, warns = self.triage_warns(bad)
            self.assertEqual(len(warns), 1, (bad, warns))
            self.assertIn("Review file structure problems", doc)
        for bad in ("- [nit] F4 Rename. (Marker: aaaaaaaaaaaa)\n", "- [nit] F4 Rename. (posted x @ 1a2b3c4)\n"):
            self.assertEqual(len(render(v2_review(nits=bad))[1]), 1, bad)

    def test_pre_v2_lines_without_ids_or_state_words_stay_clean(self):
        md = v2_review().replace("## Prior findings triaged\nNone.",
                                 "## Prior findings triaged\n- Fixed: the null check landed.\n- Refuted: bot x")
        self.assertEqual(render(md)[1], [])
        line = "- Not re-raised: F6 — Never posted, Marker text in a title\n"  # state words outside a "(" are prose
        self.assertEqual(self.triage_warns(line)[1], [])
        # A contrived pre-v2 nit that happens to say "Marker" now warns; accepted (no real file does this).
        warns = render(review(code=CARD_MD + "- [nit] Rename (Marker this as todo)\n", verdict="Request changes"))[1]
        self.assertEqual(len(warns), 1, warns)


PREV_CARD = V2_CARD.replace("F3", "F1").replace("0123456789ab", "aaaaaaaaaaa1").replace(
    "github review comment 987 @ 1a2b3c4", "https://github.com/o/r/pull/1#discussion_r5 @ 1a2b3c4")
PREV_TRIAGE = ("- Not re-raised: F3 — Old issue (Marker aaaaaaaaaaa3, Posted !1#note_3 @ 1a2b3c4)\n"
               "- Fixed: F4 — `return x` (Marker aaaaaaaaaaa4, Posted !1#note_4 @ 1a2b3c4)\n"
               "- Fixed: F5 — `ok = True`\n"
               "- Not re-raised: F6 — Never posted\n"
               "- Not re-raised: F9 — Marker only (Marker aaaaaaaaaaa9)\n")


def prev_review(card=PREV_CARD, nits="- [nit] F2 Rename `d`. (`repo/a.py:2`)\n", triage=PREV_TRIAGE,
                last="- Last ID: F10\n"):
    md = v2_review(card=card, nits=nits).replace("## Prior findings triaged\nNone.",
                                                  "## Prior findings triaged\n" + triage.rstrip("\n"))
    return md.replace("## Validation\nok\n", "## Validation\nok\n" + last, 1)


# The rewrite: F1 carried, F2 nit kept, F3 still not re-raised, F4 posted Fixed kept, F9 kept, a new F11;
# the unposted F5 (Fixed) and F6 (Not re-raised) are gone, which is allowed.
NEW_TRIAGE = PREV_TRIAGE.replace("- Fixed: F5 — `ok = True`\n", "").replace("- Not re-raised: F6 — Never posted\n", "")
NEW_CARD = PREV_CARD + V2_CARD.replace("F3", "F11").replace("**Carried:** from 1a2b3c4\n", "").replace(
    "**Marker:** 0123456789ab\n**Posted:** github review comment 987 @ 1a2b3c4\n", "")


class PreviousTests(unittest.TestCase):
    def check(self, new, old=None):
        return rr.previous_report(prev_review() if old is None else old, new)

    def test_clean_rewrite_passes(self):
        self.assertEqual(rr.render(prev_review(), "x")[1], [])
        new = prev_review(card=NEW_CARD, triage=NEW_TRIAGE, last="- Last ID: F11\n")
        self.assertEqual(rr.render(new, "x")[1], [])
        self.assertEqual(self.check(new), [])
        self.assertEqual(self.check(prev_review()), [])  # unchanged rewrite

    def test_unposted_ids_dropped_silently(self):
        for triage in (PREV_TRIAGE.replace("- Fixed: F5 — `ok = True`\n", ""),
                       PREV_TRIAGE.replace("- Not re-raised: F6 — Never posted\n", ""), NEW_TRIAGE):
            self.assertEqual(self.check(prev_review(triage=triage)), [], triage)
        self.assertEqual(self.check(prev_review(nits="")), [])  # the unposted nit F2

    def test_dropped_posted_id_warns(self):
        cases = {"F1": prev_review(card=NEW_CARD.replace(PREV_CARD, "")),
                 "F3": prev_review(triage=PREV_TRIAGE.replace(PREV_TRIAGE.splitlines()[0] + "\n", "")),
                 "F4": prev_review(triage=PREV_TRIAGE.replace(PREV_TRIAGE.splitlines()[1] + "\n", "")),
                 "F9": prev_review(triage=PREV_TRIAGE.replace(PREV_TRIAGE.splitlines()[4] + "\n", ""))}
        for fid, new in cases.items():
            out = self.check(new)
            self.assertEqual(len(out), 1, (fid, out))
            self.assertIn(fid + " ", out[0])
            self.assertIn("dropped", out[0])

    def test_posted_id_may_move_between_card_nit_and_triage(self):
        moved = PREV_TRIAGE + ("- Not re-raised: F1 — Bad thing (Marker aaaaaaaaaaa1, Posted "
                               "https://github.com/o/r/pull/1#discussion_r5 @ 1a2b3c4)\n")
        self.assertEqual(self.check(prev_review(card=NEW_CARD.replace(PREV_CARD, ""), triage=moved)), [])
        nit = "- [nit] F3 Old issue. (Marker aaaaaaaaaaa3, Posted !1#note_3 @ 1a2b3c4)\n"
        self.assertEqual(self.check(prev_review(nits=nit, triage=PREV_TRIAGE.split("\n", 1)[1])), [])

    def test_changed_or_missing_marker_or_posted_warns(self):
        cases = (("Marker", prev_review(card=PREV_CARD.replace("aaaaaaaaaaa1", "bbbbbbbbbbb1"))),
                 ("Marker", prev_review(card=PREV_CARD.replace("**Marker:** aaaaaaaaaaa1\n", ""))),
                 ("Posted", prev_review(card=PREV_CARD.replace("@ 1a2b3c4", "@ 9f9f9f9"))),
                 ("Posted", prev_review(card=re.sub(r"\*\*Posted:\*\*.*\n", "", PREV_CARD))),
                 ("Marker", prev_review(triage=PREV_TRIAGE.replace("aaaaaaaaaaa4", "ccccccccccc4"))),
                 ("Posted", prev_review(triage=PREV_TRIAGE.replace(", Posted !1#note_3 @ 1a2b3c4", ""))))
        for field, new in cases:
            out = self.check(new)
            self.assertEqual(len(out), 1, (field, out))
            self.assertIn(field, out[0])
        # gaining a Posted value (a new post) is fine
        self.assertEqual(self.check(prev_review(triage=PREV_TRIAGE.replace(
            "(Marker aaaaaaaaaaa9)", "(Marker aaaaaaaaaaa9, Posted !1#note_9 @ 1a2b3c4)"))), [])

    def test_lower_last_id_or_max_id_warns(self):
        out = self.check(prev_review(last="- Last ID: F9\n"))
        self.assertEqual(len(out), 1, out)
        self.assertIn("Last ID", out[0])
        out = self.check(prev_review(last=""))
        self.assertTrue(out and all("Last ID" in w or "max ID" in w for w in out), out)
        # an old file without Last ID: its max ID is the floor
        old = prev_review(last="")
        self.assertEqual(self.check(prev_review(last=""), old), [])
        out = self.check(prev_review(last="", triage=NEW_TRIAGE.replace(PREV_TRIAGE.splitlines()[4] + "\n", "")
                                     + "- Not re-raised: F9 — Marker only (Marker aaaaaaaaaaa9)\n"), old)
        self.assertEqual(out, [])
        out = self.check(prev_review(last="", triage=PREV_TRIAGE.replace("F9", "F8").replace("aaaaaaaaaaa9", "x" * 12)),
                         old)
        self.assertTrue(any("max ID" in w for w in out), out)

    def test_reused_id_warns(self):
        reuse = NEW_CARD.replace("F11", "F7")  # F7 was below Last ID F10 and not in the old file
        out = self.check(prev_review(card=reuse, triage=NEW_TRIAGE))
        self.assertEqual(len(out), 1, out)
        self.assertIn("F7", out[0])
        self.assertIn("reuse", out[0])
        reuse = NEW_CARD.replace("F11", "F5")  # F5 is in the old file (an unposted Fixed): not detected as reuse
        self.assertEqual(self.check(prev_review(card=reuse, triage=NEW_TRIAGE)), [])

    def test_posted_nit_in_a_nit_only_file(self):
        nit = "- [nit] F2 Rename `d`. (`repo/a.py:2`) (Marker aaaaaaaaaaa2, Posted !1#note_2 @ 1a2b3c4)\n"
        for last, triage in (("- Last ID: F2\n", ""), ("", ""), ("", "- Fixed: F1 — `ok`\n")):
            old = prev_review(card=CARD_MD, nits=nit, triage=triage or "None.\n", last=last)
            self.assertEqual(rr.posted_state(old)[0][2], ("F2", "aaaaaaaaaaa2", "!1#note_2 @ 1a2b3c4"), last)
            self.assertEqual(self.check(old, old), [], last)
            out = self.check(prev_review(card=CARD_MD, nits="", triage=triage or "None.\n", last=last), old)
            self.assertTrue(any("F2 " in w and "dropped" in w for w in out), (last, out))
        # render reads the same nit ID (shown as an ID tag) under the same rule
        doc, warns = render(prev_review(card=CARD_MD, nits=nit, triage="None.\n", last=""))
        self.assertEqual(warns, [])
        self.assertIn("<code>F2</code> Rename", doc)
        doc, warns = render(prev_review(card=CARD_MD, nits="- [nit] F2 Rename.\n", triage="None.\n", last="- Last ID: F2\n"))
        self.assertEqual(warns, [])
        self.assertIn("<code>F2</code> Rename", doc)

    def test_near_miss_lines_in_either_file_are_printed(self):
        bad = PREV_TRIAGE.replace("(Marker aaaaaaaaaaa4, Posted !1#note_4 @ 1a2b3c4)", "(Marker aaaaaaaaaaa4) trailing")
        old = prev_review(triage=bad)
        new = prev_review(triage=bad.replace(bad.splitlines()[1] + "\n", ""))  # F4 dropped
        out = self.check(new, old)
        self.assertTrue(any(w.startswith("old file: ") and "F4" in w and "near-miss" in w for w in out), out)
        out = self.check(old, prev_review())
        self.assertTrue(any(w.startswith("new file: ") and "F4" in w for w in out), out)
        out = self.check(prev_review(triage=PREV_TRIAGE + "- **Fixed:** F7 — `x`\n"))
        self.assertTrue(any(w.startswith("new file: ") for w in out), out)

    def test_trailing_period_is_not_a_change(self):
        new = prev_review(triage=PREV_TRIAGE.replace("@ 1a2b3c4)\n", "@ 1a2b3c4).\n"))
        self.assertEqual(self.check(new), [])

    def test_cli_modes_are_exclusive_and_extra_paths_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            md = Path(d) / "review.md"
            md.write_text(prev_review(), encoding="utf-8")
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            base = [sys.executable, str(SCRIPTS / "render_review.py")]
            for args in (["--previous", str(md), "--in-diff", str(md), str(md)],
                         ["--marker", "mr-1", "canonical", "F1", "--previous", str(md), str(md)],
                         ["--marker", "mr-1", "canonical", "F1", str(md)],
                         ["--previous", str(md), str(md), str(md)],
                         [str(md), str(md)]):
                r = subprocess.run(base + args, capture_output=True, text=True, env=env)
                self.assertEqual((r.returncode, r.stdout), (2, ""), args)
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ["review.md"])

    def test_cli_prints_problems_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            old, new = Path(d) / "old.md", Path(d) / "review.md"
            old.write_text(prev_review(), encoding="utf-8")
            new.write_text(prev_review(last="- Last ID: F9\n"), encoding="utf-8")
            cmd = [sys.executable, str(SCRIPTS / "render_review.py"), "--previous", str(old), str(new)]
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            r = subprocess.run(cmd, capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 1, r.stderr)  # an actionable line: exit 1
            self.assertEqual(len(r.stdout.splitlines()), 1, r.stdout)
            self.assertIn("Last ID", r.stdout)
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ["old.md", "review.md"])
            new.write_text(prev_review(), encoding="utf-8")
            r = subprocess.run(cmd, capture_output=True, text=True, env=env)
            self.assertEqual((r.returncode, r.stdout), (0, ""))
            r = subprocess.run(cmd[:3] + [str(Path(d) / "missing.md"), str(new)], capture_output=True, text=True,
                               env=env)
            self.assertEqual((r.returncode, r.stdout), (1, ""))


class BranchReviewFixTests(unittest.TestCase):
    """Task 9a: the guard's exit code, backtick spans in near-miss detection, Last ID below the max ID,
    the collapsed-nit line and a backticked Since."""

    def run_previous(self, old_md, new_md):
        with tempfile.TemporaryDirectory() as d:
            old, new = Path(d) / "old.md", Path(d) / "review.md"
            old.write_text(old_md, encoding="utf-8")
            new.write_text(new_md, encoding="utf-8")
            cmd = [sys.executable, str(SCRIPTS / "render_review.py"), "--previous", str(old), str(new)]
            return subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))

    def test_previous_exit_codes(self):
        r = self.run_previous(prev_review(), prev_review(last="- Last ID: F9\n"))  # actionable
        self.assertEqual(r.returncode, 1, r.stdout)
        r = self.run_previous(prev_review(), prev_review())
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_state_words_inside_backtick_code_are_not_near_misses(self):
        for line in ("- Fixed: F6 — `value = get(marker)` returns early\n",
                     '- Fixed: F6 — `setState("posted")` now runs once\n',
                     "- Not re-raised: F6 — Uses `(marker)` again (Marker aaaaaaaaaaaa)\n"):
            md = v2_review().replace("## Prior findings triaged\nNone.", "## Prior findings triaged\n" + line)
            self.assertEqual(render(md)[1], [], line)
        self.assertEqual(render(v2_review(nits="- [nit] F4 Rename `get(posted)`. (`repo/a.py:2`)\n"))[1], [])
        # outside a code span it still warns, and a real tail is still parsed and checked
        md = v2_review().replace("## Prior findings triaged\nNone.",
                                 "## Prior findings triaged\n- Fixed: F6 — `x` (marker aaaaaaaaaaaa)\n")
        self.assertEqual(len(render(md)[1]), 1)
        self.assertEqual(rr.parse_tail("`get(marker)` (Marker aaaaaaaaaaaa)"), ("aaaaaaaaaaaa", None, None))

    def test_last_id_below_the_highest_used_id_warns(self):
        doc, warns = render(prev_review(last="- Last ID: F8\n"))  # F9 is in the triage
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("Last ID F8", warns[0])
        self.assertIn("F9", warns[0])
        self.assertIn("Review file structure problems", doc)
        self.assertEqual(render(prev_review(last="- Last ID: F9\n"))[1], [])
        self.assertEqual(render(prev_review(last=""))[1], [])  # no Last ID line: nothing to compare

    def test_collapsed_nit_line_is_shown_but_not_counted(self):
        nits = "- [nit] F4 Rename `d` to `delay`. (`repo/a.py:2`)\n- [nit] 3 more not shown: naming, spacing, typo\n"
        doc, warns = render(v2_review(nits=nits))
        self.assertEqual(warns, [])
        self.assertIn("<strong>2</strong><span>findings</span>", doc)  # the card and one nit
        self.assertIn('<span class="group-count">2</span>', doc)
        self.assertIn("3 more not shown: naming, spacing, typo", doc)
        base = render(v2_review())[0]
        self.assertIn("<strong>2</strong><span>findings</span>", base)

    def test_backticked_since_is_stripped_like_head_sha(self):
        doc, warns = render(v2_review(header="**Mode:** since-last\n**Since:** `1a2b3c4`\n"))
        self.assertEqual(warns, [])
        self.assertIn("<dt>Since</dt><dd><code>1a2b3c4</code></dd>", doc)
        self.assertTrue(render(v2_review(header="**Since:** `abc12`\n"))[1])


class ReconcileTests(unittest.TestCase):
    """Task 9a fix pass: guard on unreadable old tails, narrower backtick strip, collapsed-nit near
    misses, Dropped IDs in the Last ID check."""

    F4 = "(Marker aaaaaaaaaaa4, Posted !1#note_4 @ 1a2b3c4)"

    def guard(self, old_tail, new_tail, old_title="`return x`"):
        """-> the --previous run for an F4 triage line rewrite (None as new_tail drops F4)."""
        line = PREV_TRIAGE.splitlines()[1] + "\n"
        old = prev_review(triage=PREV_TRIAGE.replace(line, "- Fixed: F4 — %s %s\n" % (old_title, old_tail)))
        new = prev_review(triage=PREV_TRIAGE.replace(line, "" if new_tail is None else
                                                     "- Fixed: F4 — `return x` %s\n" % new_tail))
        return BranchReviewFixTests.run_previous(self, old, new)

    def assertUnrepairable(self, r, code):
        out = r.stdout.splitlines()
        self.assertEqual(r.returncode, code, r.stdout)
        self.assertEqual([w for w in out if w.startswith("unrepairable: ")],
                         ["unrepairable: F4 has a malformed or unreadable Marker/Posted in the old file; "
                          "mark it do-not-post and ask the user"], r.stdout)
        self.assertTrue(any(w.startswith("old file: ") for w in out), r.stdout)

    def test_unrepairable_old_values_exit_3_whether_carried_or_corrected(self):
        cases = ("(Marker aaaaaaaaaaa4, Posted !1#note_4)",  # no " @ "
                 "(marker aaaaaaaaaaa4, Posted !1#note_4 @ 1a2b3c4)",  # near miss, a commit hash in the text
                 "(Marker XYZ, Posted !1#note_4 @ 1a2b3c4)")
        for old_tail in cases:
            title = "`return x` at 1a2b3c4d" if "marker" in old_tail else "`return x`"
            self.assertUnrepairable(self.guard(old_tail, old_tail, title), 3)  # carried verbatim
            self.assertUnrepairable(self.guard(old_tail, self.F4, title), 3)  # corrected
            # only the malformed half goes uncompared: changing or dropping the valid half is actionable;
            # a near-miss tail has no readable half
            valid_half = 3 if "(marker" in old_tail else 1
            self.assertUnrepairable(self.guard(old_tail, "(Marker bbbbbbbbbbbb)", title), valid_half)
            self.assertUnrepairable(self.guard(old_tail, "", title), valid_half)

    def test_dropping_an_unrepairable_id_or_mixing_in_an_actionable_line_exits_1(self):
        r = self.guard("(Marker XYZ, Posted !1#note_4 @ 1a2b3c4)", None)
        self.assertUnrepairable(r, 1)  # dropped
        self.assertTrue(any("F4" in w and "missing from the new file" in w for w in r.stdout.splitlines()), r.stdout)
        old = prev_review(triage=PREV_TRIAGE.replace(self.F4, "(Marker XYZ, Posted !1#note_4 @ 1a2b3c4)"))
        r = BranchReviewFixTests.run_previous(self, old, prev_review(last="- Last ID: F9\n"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertTrue(any(w.startswith("unrepairable: F4") for w in r.stdout.splitlines()), r.stdout)
        # a new malformed value that differs from the old one stays a new-file problem
        r = self.guard("(Marker XYZ, Posted !1#note_4 @ 1a2b3c4)", "(Marker QQQ, Posted !1#note_4 @ 1a2b3c4)")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertTrue(any(w.startswith("new file: ") for w in r.stdout.splitlines()), r.stdout)

    def test_unrepairable_card_value(self):
        old = prev_review(card=PREV_CARD.replace("aaaaaaaaaaa1", "AAAAAAAAAAA1"))
        r = BranchReviewFixTests.run_previous(self, old, prev_review())
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("unrepairable: F1 ", r.stdout)

    def test_bold_label_old_line_is_unrepairable_whether_carried_or_rewritten(self):
        line = PREV_TRIAGE.splitlines()[1] + "\n"
        bold = "- **Fixed:** F4 — x (Marker aaaaaaaaaaa4, Posted !1#note_4 @ 1a2b3c4)\n"
        old = prev_review(triage=PREV_TRIAGE.replace(line, bold))
        for new_line in (bold, "- Fixed: F4 — x (Marker aaaaaaaaaaa4, Posted !1#note_4 @ 1a2b3c4)\n"):
            r = BranchReviewFixTests.run_previous(self, old, prev_review(triage=PREV_TRIAGE.replace(line, new_line)))
            self.assertEqual(r.returncode, 3, (new_line, r.stdout))
        r = BranchReviewFixTests.run_previous(self, old, prev_review(triage=PREV_TRIAGE.replace(line, "")))
        self.assertEqual(r.returncode, 1, r.stdout)  # dropped

    def test_valid_half_of_an_unrepairable_id_is_still_compared(self):
        r = self.guard("(Marker aaaaaaaaaaa4, Posted !1#note_4 @ ZZZ)", "(Marker bbbbbbbbbbbb, Posted !1#note_4 @ ZZZ)")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("F4 Marker changed", r.stdout)
        r = self.guard("(Marker aaaaaaaaaaa4, Posted !1#note_4 @ ZZZ)", "(Marker aaaaaaaaaaa4, Posted !1#note_4 @ 1a2b3c4)")
        self.assertEqual(r.returncode, 3, r.stdout)

    def test_usage_error_exits_2_and_the_command_never_accepts_2(self):
        r = subprocess.run([sys.executable, str(SCRIPTS / "render_review.py"), "--previous"], capture_output=True,
                           text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(r.returncode, 2)
        cmd = (SCRIPTS.parent / "commands" / "review-mr.md").read_text(encoding="utf-8")
        self.assertIn("until it exits 0 or 3", cmd)
        self.assertNotIn("exits 0 or 2", cmd)

    def triage(self, line):
        return render(v2_review().replace("## Prior findings triaged\nNone.", "## Prior findings triaged\n" + line))[1]

    def test_code_span_tails_still_warn(self):
        for line in ("- Fixed: F6 — x (`Marker aaaaaaaaaaaa`)\n",
                     "- Fixed: F6 — fixed `(Marker aaaaaaaaaaaa, Posted !1#note_3 @ 1a2b3c4)` now\n",
                     "- Fixed: F6 — done `(Posted !7#note_2 @ abcdef1)`\n",
                     "- Fixed: F6 — done `(posted !7#note_2 @ abcdef1)`\n"):
            self.assertEqual(len(self.triage(line)), 1, line)
        for line in ("- Fixed: F6 — `value = get(marker)` returns early\n",
                     '- Fixed: F6 — `setState("posted")` now runs once\n'):
            self.assertEqual(self.triage(line), [], line)

    def test_collapsed_nit_near_misses_warn_and_count(self):
        for text in ("0 more not shown: x", "03 more not shown: x", "three more not shown: x",
                     "3 more not shown x", "3 More not shown: x"):
            doc, warns = render(v2_review(nits="- [nit] " + text + "\n"))
            self.assertEqual(len(warns), 1, (text, warns))
            self.assertIn("more not shown", warns[0])
            self.assertIn("<strong>2</strong><span>findings</span>", doc)  # counted as an ordinary nit
        self.assertEqual(render(v2_review(nits="- [nit] 3 more not shown: x\n"))[1], [])

    def test_last_id_counts_dropped_ids(self):
        warns = render(prev_review(last="- Dropped F12: no counter-case held\n- Last ID: F10\n"))[1]
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("F12", warns[0])
        self.assertEqual(render(prev_review(last="- Dropped F10: x\n- Last ID: F10\n"))[1], [])

    def test_titled_loss_lines(self):
        warns = render(prev_review(last="- Dropped F12: Retry loops forever — `break` at a.py:3\n- Last ID: F10\n"))[1]
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("F12", warns[0])
        titled = ("- Dropped F10: Retry loops forever — `break` at a.py:3\n"
                  "- Downgraded F9: important→minor, Slow query — only runs in the nightly job\n- Last ID: F10\n")
        self.assertEqual(render(prev_review(last=titled))[1], [])


class CssTests(unittest.TestCase):
    TEXT_VARS = {"text", "muted", "accent", "ok", "sev-critical", "sev-important", "sev-minor", "sev-nit"}
    SURFACES = ("bg", "surface", "surface-2")

    @classmethod
    def setUpClass(cls):
        cls.doc = render(sample())[0]
        cls.css = re.search(r"<style>\n(.*?)</style>", cls.doc, re.S).group(1)
        cls.roots = [dict(re.findall(r"--([\w-]+):\s*([^;]+);", b))
                     for b in re.findall(r":root\s*\{([^}]*)\}", cls.css)]

    def test_csp_first_in_head(self):
        head = self.doc.split("<head>\n")[1]
        self.assertTrue(head.startswith('<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
                                        "style-src 'unsafe-inline'; img-src data:; base-uri 'none'; "
                                        "form-action 'none'\">"))
        self.assertNotRegex(self.doc, r"<script|https?://|@import|url\(")

    def test_original_stylesheet_no_foreign_names(self):
        banned = ["affin" + "idi", "fig" + "tree", "fat" + "frank", "design" + "-token"]
        self.assertNotRegex(self.doc, "(?i)" + "|".join(banned))
        self.assertIn("original to bq", Path(rr.__file__).read_text(encoding="utf-8"))

    def test_no_color_literals_outside_root(self):
        rest = re.sub(r":root\s*\{[^}]*\}", "", self.css)
        self.assertNotRegex(rest, r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(")
        self.assertEqual(len(self.roots), 3)  # light + dark + print
        self.assertIn("@media (prefers-color-scheme:dark)", self.css)

    def test_all_vars_defined(self):
        used = set(re.findall(r"var\(--([\w-]+)", self.css))
        self.assertLessEqual(used, set(self.roots[0]))
        for r in self.roots[1:]:
            self.assertLessEqual(set(r), set(self.roots[0]))
        for r in self.roots:  # dark and print redefine every colour variable
            if r is not self.roots[0]:
                self.assertTrue({k for k in self.roots[0] if not k.startswith(("sp-", "r-", "font", "fs-", "measure"))} <= set(r))

    def test_scrollable_regions_are_keyboard_reachable(self):
        doc = render(sample())[0]
        self.assertRegex(doc, r'<div class="table-wrap" tabindex="0" role="region" aria-label="[^"]+">')
        self.assertRegex(doc, r'<div class="diff" tabindex="0" role="region"')
        self.assertNotIn("<script", doc)

    def test_severity_and_verdict_are_word_plus_glyph(self):
        doc = render(sample())[0]
        self.assertIn('<span aria-hidden="true">\u25b2</span> Important', doc)
        self.assertIn('<span class="glyph" aria-hidden="true">\u2716</span><span>Request changes</span>', doc)

    def test_severity_bar_segments_are_integers(self):
        doc = render(sample())[0]
        self.assertEqual(re.findall(r'class="seg tone-(\w+)" style="flex-grow:(\d+)"', doc),
                         [("important", "2"), ("nit", "1")])

    def test_focus_and_print(self):
        self.assertIn(":focus-visible{outline:2px solid var(--focus);outline-offset:2px}", self.css)
        self.assertIn("@media print", self.css)

    def test_contrast_light_dark_print(self):
        used = set(re.findall(r"(?<![-\w])color:\s*var\(--([\w-]+)\)", self.css))
        self.assertLessEqual(used, self.TEXT_VARS)
        for i, root in enumerate(self.roots):
            tokens = dict(self.roots[0], **root)
            surfaces = {n: parse(tokens[n]) for n in self.SURFACES}
            for name in sorted(self.TEXT_VARS):
                fg = parse(tokens[name])
                backgrounds = dict(surfaces)
                if name + "-bg" in tokens:  # a tone colour is also drawn on its own tint
                    for sn, sv in surfaces.items():
                        backgrounds[name + "-bg over " + sn] = over(parse(tokens[name + "-bg"]), sv)
                for bn, bg in backgrounds.items():
                    ratio = contrast(over(fg, bg), bg)
                    self.assertGreaterEqual(ratio, 4.5, "%s on %s (theme %d): %.2f" % (name, bn, i, ratio))
            for sn, sv in surfaces.items():
                self.assertGreaterEqual(contrast(parse(tokens["focus"]), sv), 3.0, "focus on %s (theme %d)" % (sn, i))


def parse(v):
    v = v.strip()
    if v.startswith("#"):
        h = v[1:]
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (1.0,)
    m = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)", v)
    return int(m.group(1)) / 255, int(m.group(2)) / 255, int(m.group(3)) / 255, float(m.group(4))


def over(fg, bg):
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3)) + (1.0,)


def lum(c):
    lin = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c[:3]]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


if __name__ == "__main__":
    unittest.main()
