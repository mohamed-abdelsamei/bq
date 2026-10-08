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
        self.assertEqual(nums(rows[2]), ["1", "0", "0", "1", "Yes"])   # important
        self.assertEqual(nums(rows[3]), ["0", "1", "0", "1", "No"])    # minor
        self.assertEqual(nums(rows[4]), ["1", "0", "0", "1", "No"])    # nit
        self.assertEqual(nums(rows[5])[:4], ["2", "1", "0", "3"])      # totals
        self.assertNotIn("cards parsed", doc)
        self.assertNotIn("contradicts", doc)
        self.assertIn("Proposed patch (not posted)", doc)
        self.assertIn('class="ln add">+for _ in range(MAX_ATTEMPTS):', doc)
        self.assertEqual(doc.count("Head SHA: <code>4f2a9c1</code>"), 3)  # two cards + footer
        self.assertIn('<span class="tag blocking">Blocking</span>', doc)
        self.assertIn('<span class="tag">Non-blocking</span>', doc)
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
        md = sample().replace("### [important]", "### [urgent]")
        self.assertIn("1 of 2 cards parsed", render(md)[0])

    def test_contradictions(self):
        base = sample()
        d = render(base.replace("**Verdict:** Request changes", "**Verdict:** Approve", 1))[0]
        self.assertIn("Verdict contradicts findings", d)
        d = render(base.replace("**Verdict:** Request changes", "**Verdict:** Approve with changes", 1))[0]
        self.assertIn("Verdict contradicts findings", d)
        none = re.sub(r"### \[important\].*?(?=- \[nit\])", "", base, flags=re.S)
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
                         [("important", "1"), ("minor", "1"), ("nit", "1")])

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
