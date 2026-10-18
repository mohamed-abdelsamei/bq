#!/usr/bin/env python3
"""Render a /bq:review-mr report (markdown) to one self-contained HTML file. Stdlib only.

Usage: python3 scripts/render_review.py <review.md> [-o out.html]
       python3 scripts/render_review.py --in-diff <diff-file> [--repo <name>] <review.md>
       python3 scripts/render_review.py --previous <old.md> <review.md>
       python3 scripts/render_review.py --marker <key> <source> <ID>

--in-diff prints `<ID or title>\t<anchor>\tyes|no|nofile|malformed` for each card with an Anchor, computed
from a `git diff -U0` file (git diff output with `diff --git` headers), and writes nothing.
--previous prints one line per posted-state problem of a canonical rewrite against the file it replaces
(nothing when clean) and writes nothing; it exits 1 when a line is actionable (anything but the
informational `old file:` and `unrepairable:` lines), else 3 when an `unrepairable:` line is printed
(ask the user), else 0; 2 is a usage error. --marker prints the 12-hex posting marker.

The md is the source of truth (format: skills/mr-review/references/report-format.md); the html is
derived and regenerable. Same input gives byte-identical output (no timestamps). Parsing is strict:
a `###` card that does not parse is shown escaped under a visible "N of M cards parsed" banner, never
dropped, and counts come only from parsed cards. Odd input shows visible banners in the html and warnings on stderr (exit 0);
the exit code is non-zero only when the input file cannot be read (or the output cannot be written), or
when --previous prints an actionable (1) or unrepairable (3) line.

Every md-derived string is escaped with html.escape(quote=True). There is no raw HTML and no links.
"""
import argparse
import codecs
import hashlib
import html
import re
import sys
from pathlib import Path

SEVERITIES = ("critical", "important", "minor", "nit")
BLOCKING = ("critical", "important")
AXES = ("code", "business", "process")
CONFIDENCE = ("confirmed", "suspected")
VERDICTS = ("Approve", "Approve with changes", "Request changes")
HEADER_KEYS = ("MR", "Title", "Head SHA", "Target", "Date", "Reviewers", "Verdict")  # required
OPTIONAL_HEADER_KEYS = ("Mode", "Since", "Ticket")  # absent is fine; shown in the masthead when present
MODES = ("fresh", "full", "since-last")
SHA_RE = re.compile(r"[0-9a-f]{7,40}")
# Lenient: a Ticket header needs a state on at least one key: a "(...)" group holding "fetched" or
# "not fetched", after an optional source ("(branch, fetched via x)"). Odd cases stay unwarned.
TICKET_STATE_RE = re.compile(r"\([^)]*\b(?:not )?fetched\b", re.I)
META_ORDER = ("MR", "Head SHA", "Target", "Date", "Reviewers", "Mode", "Since", "Ticket",
              "Title")  # Title last: it can be long
IN_DIFF = ("yes", "no")
SECTIONS = (  # (heading, axis for findings sections or None)
    ("Code findings", "code"),
    ("Business findings", "business"),
    ("Process & convention findings", "process"),
    ("Prior findings triaged", None),
    ("Validation", None),
    ("Verdict", None),
)
GLYPH = {"critical": "✖", "important": "▲", "minor": "●", "nit": "○"}
SEV_TONE = {s: s for s in SEVERITIES}
VERDICT_TONE = {"Approve": "ok", "Approve with changes": "important", "Request changes": "critical"}
VERDICT_GLYPH = {"Approve": "✔", "Approve with changes": "◆", "Request changes": "✖"}
PATCH_LABEL = "Proposed patch (not posted)"

# The stylesheet is original to bq: a cool, modern "review dossier" (slate ink on a cool-grey page with
# white cards in light, deep navy in dark, one teal accent; severity hues only as slim inset bars,
# markers and small labels), a dark variant under prefers-color-scheme, and a print override. System
# font stacks only. Colour literals live only in the :root blocks; severity and verdict are always a
# word plus a glyph, never colour alone. Tones: critical/important/minor/nit for severities, ok for the
# approving verdict.
CSS_BASE = """\
:root{
--bg:#F4F6F9;--surface:#FFFFFF;--surface-2:#EEF2F6;
--text:#0F172A;--muted:#475569;
--border:#E2E8F0;--border-strong:#CBD5E1;--shadow:rgba(15,23,42,.06);--shadow-2:rgba(15,23,42,.07);--hl:rgba(255,255,255,0);
--accent:#0B6B84;--accent-bg:rgba(14,116,144,.09);--accent-line:rgba(14,116,144,.35);--focus:#0E7490;
--sev-critical:#BE123C;--sev-critical-bg:rgba(190,18,60,.07);--sev-critical-line:rgba(190,18,60,.3);
--sev-important:#A8480A;--sev-important-bg:rgba(180,83,9,.09);--sev-important-line:rgba(180,83,9,.32);
--sev-minor:#1D4ED8;--sev-minor-bg:rgba(29,78,216,.07);--sev-minor-line:rgba(29,78,216,.3);
--sev-nit:#475569;--sev-nit-bg:rgba(71,85,105,.08);--sev-nit-line:rgba(71,85,105,.3);
--ok:#166534;--ok-bg:rgba(22,101,52,.08);--ok-line:rgba(22,101,52,.3);
--sp-1:2px;--sp-2:4px;--sp-3:8px;--sp-4:12px;--sp-5:16px;--sp-6:24px;--sp-7:40px;--sp-8:64px;
--fs-label:.6875rem;--fs-0:.75rem;--fs-1:.875rem;--fs-2:.9375rem;--fs-3:1.125rem;--fs-4:1.5rem;--fs-5:2.5rem;
--r-1:6px;--r-2:10px;--r-3:14px;
--measure:75ch;
--font-sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI Variable Text","Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
--font-mono:ui-monospace,"SF Mono","Cascadia Mono",Menlo,Consolas,monospace;
}
*,*::before,*::after{box-sizing:border-box}
html{color-scheme:light dark}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font-sans);font-size:var(--fs-2);line-height:1.6;font-feature-settings:'cv11','ss01';-webkit-font-smoothing:antialiased;-webkit-text-size-adjust:100%}
main{max-width:70rem;margin:0 auto;padding:var(--sp-6) var(--sp-6) var(--sp-8)}
h1,h2,h3{overflow-wrap:anywhere;text-wrap:balance;letter-spacing:-.02em}
h2{font-size:var(--fs-4);line-height:1.2;font-weight:700;margin:var(--sp-7) 0 var(--sp-4);display:flex;align-items:center;gap:var(--sp-3)}
h3{font-size:var(--fs-3);line-height:1.3;font-weight:700;margin:0}
p{margin:0 0 var(--sp-3)}
ul,ol{margin:0 0 var(--sp-3);padding-left:var(--sp-6)}
code{font-family:var(--font-mono);font-size:.9em;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--r-1);padding:0 .35em;overflow-wrap:anywhere}
pre{font-family:var(--font-mono);font-size:var(--fs-1);background:var(--surface-2);border:1px solid var(--border);border-radius:var(--r-2);padding:var(--sp-4);margin:0 0 var(--sp-3);overflow-x:auto}
pre code{background:none;border:0;padding:0;font-size:inherit}
.label,.eyebrow,dt,thead th{font-size:var(--fs-label);font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.eyebrow{margin:0 0 var(--sp-2);color:var(--accent)}
.masthead{margin:0 0 var(--sp-5)}
.masthead::before{content:"";display:block;width:2.5rem;height:3px;border-radius:3px;background:var(--accent);margin:0 0 var(--sp-4)}
.masthead h1{font-size:clamp(1.75rem,1.2rem + 1.8vw,2.5rem);line-height:1.15;font-weight:700;margin:0 0 var(--sp-4)}
.meta{display:flex;flex-wrap:wrap;gap:var(--sp-2) var(--sp-6);margin:0;font-size:var(--fs-1);font-variant-numeric:tabular-nums}
.meta div{display:flex;align-items:baseline;gap:var(--sp-3);min-width:0}
.meta .wide{flex-basis:100%}
.meta dd{margin:0;overflow-wrap:anywhere;font-weight:500}
.meta code{font-size:.9em}
.banner{position:relative;border:1px solid var(--border-strong);border-radius:var(--r-3);padding:var(--sp-4) var(--sp-5) var(--sp-4) var(--sp-6);margin:0 0 var(--sp-4);background:linear-gradient(var(--surface),var(--surface))}
.banner::before{content:"";position:absolute;left:var(--sp-3);top:var(--sp-4);bottom:var(--sp-4);width:3px;border-radius:3px;background:var(--border-strong)}
.banner p{margin:0 0 var(--sp-2);max-width:var(--measure);font-size:var(--fs-1)}
.banner p:last-child{margin-bottom:0}
.lead{font-weight:700;font-size:var(--fs-2)}
.lead>span{display:inline-block;margin-right:var(--sp-2)}
.hero{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:var(--sp-5);align-items:start;margin:0 0 var(--sp-6)}
.card,.verdict,.finding,.nits,.patch{box-shadow:0 1px 2px var(--shadow),0 4px 12px var(--shadow-2),inset 0 1px 0 var(--hl)}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-3)}
.verdict{position:relative;border:1px solid var(--border-strong);border-radius:var(--r-3);padding:var(--sp-5) var(--sp-6) var(--sp-5) var(--sp-7);background:linear-gradient(var(--surface),var(--surface))}
.verdict::before{content:"";position:absolute;left:var(--sp-4);top:var(--sp-5);bottom:var(--sp-5);width:3px;border-radius:3px;background:var(--border-strong)}
.verdict .eyebrow{color:var(--muted)}
.verdict-word{font-size:var(--fs-5);line-height:1.05;letter-spacing:-.02em;font-weight:700;margin:0 0 var(--sp-4);display:flex;align-items:baseline;gap:var(--sp-3)}
.verdict-word .glyph{font-size:.7em;flex:none}
.fix{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-2);padding:var(--sp-3) var(--sp-5) var(--sp-4);margin:0 0 var(--sp-3)}
.fix .label{color:var(--accent);margin:0 0 var(--sp-1)}
.fix .text{font-size:1.0625rem;line-height:1.45;font-weight:600;letter-spacing:-.01em;margin:0;max-width:var(--measure);overflow-wrap:anywhere}
.strengths{font-size:var(--fs-1);color:var(--text);margin:0;max-width:var(--measure)}
.overview{padding:var(--sp-4) var(--sp-5) var(--sp-3)}
.overview h2{font-size:var(--fs-label);font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:0 0 var(--sp-3);display:block}
.overview .stat{display:flex;align-items:baseline;gap:var(--sp-2) var(--sp-3);flex-wrap:wrap;margin:0 0 var(--sp-3);color:var(--muted);font-size:var(--fs-1);font-variant-numeric:tabular-nums}
.overview .stat strong{font-size:var(--fs-4);line-height:1;font-weight:700;letter-spacing:-.02em;color:var(--text)}
.overview .stat strong+span{margin-right:var(--sp-4)}
.bar{display:flex;gap:2px;height:.625rem;margin:0 0 var(--sp-3);background:var(--surface-2);border-radius:99px;padding:2px;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.seg{flex-basis:0;min-width:.5rem;border-radius:99px}
.table-wrap{overflow-x:auto;margin:0}
table{border-collapse:collapse;width:100%;font-size:var(--fs-1);font-variant-numeric:tabular-nums}
caption{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
th,td{padding:var(--sp-2) var(--sp-2);border-bottom:1px solid var(--border);text-align:left}
td.num,th.num{text-align:center}
thead th{text-align:left;border-bottom-color:var(--border-strong)}
thead th.num{text-align:center}
tfoot th,tfoot td{border-bottom:0;font-weight:700}
tbody th,tfoot th{white-space:nowrap;font-weight:500;text-transform:none;font-size:var(--fs-1);letter-spacing:0;color:var(--text)}
.sev{font-weight:700;font-size:var(--fs-1);white-space:nowrap}
.group-count{font-size:var(--fs-0);font-weight:600;letter-spacing:0;color:var(--muted);background:var(--surface-2);border:1px solid var(--border);border-radius:99px;padding:0 var(--sp-3);font-variant-numeric:tabular-nums}
.finding{position:relative;background:var(--surface);border:1px solid var(--border);border-radius:var(--r-3);padding:0 var(--sp-6) var(--sp-4) var(--sp-7);margin:0 0 var(--sp-4)}
.finding::before{content:"";position:absolute;left:var(--sp-4);top:var(--sp-4);bottom:var(--sp-4);width:3px;border-radius:3px;background:var(--border-strong)}
.f-head{padding:var(--sp-4) 0 var(--sp-3);margin:0 0 var(--sp-4);border-bottom:1px solid var(--border)}
.f-head h3{margin:0 0 var(--sp-3)}
.f-meta{display:flex;flex-wrap:wrap;align-items:center;gap:var(--sp-2) var(--sp-3);margin:0}
.tag{display:inline-block;border:1px solid var(--border-strong);border-radius:99px;padding:0 var(--sp-3);font-size:var(--fs-0);font-weight:600;white-space:nowrap;color:var(--muted)}
.tag.blocking{color:var(--text);background:var(--surface-2)}
.tag.confirmed{color:var(--accent);border-color:var(--accent-line);background:var(--accent-bg)}
.tag.suspected{color:var(--muted);border-style:dashed;font-style:italic}
.anchor{color:var(--accent);font-size:var(--fs-0);background:var(--accent-bg);border:1px solid var(--accent-line);border-radius:99px;padding:0 var(--sp-3);max-width:100%}
.rows{display:grid;grid-template-columns:5rem minmax(0,1fr);gap:var(--sp-2) var(--sp-4);margin:0}
.rows dt{padding-top:.2rem}
.rows dd{margin:0;min-width:0;overflow-wrap:anywhere}
.rows dd>*:last-child{margin-bottom:0}
.rows p,.rows ul,.rows ol{max-width:var(--measure)}
.rows dt.wide,.rows dd.wide{grid-column:1/-1}
.rows dt.wide{margin-top:var(--sp-2);margin-bottom:calc(-1*var(--sp-2))}
.rows dd.quote{border-left:2px solid var(--border-strong);padding-left:var(--sp-4);color:var(--muted);font-size:var(--fs-1)}
.f-foot{margin:var(--sp-4) 0 0;padding-top:var(--sp-3);border-top:1px solid var(--border);color:var(--muted);font-size:var(--fs-0)}
.patch{border:1px solid var(--border-strong);border-radius:var(--r-2);margin:var(--sp-2) 0;background:var(--surface);overflow:hidden;box-shadow:none}
.patch-bar{background:var(--surface-2);color:var(--muted);border-bottom:1px solid var(--border-strong);font-family:var(--font-mono);font-size:var(--fs-0);font-weight:600;padding:var(--sp-2) var(--sp-4)}
.diff{font-family:var(--font-mono);font-size:.8125rem;line-height:1.55;overflow-x:auto;padding:var(--sp-3) 0}
.ln{display:block;white-space:pre;padding:0 var(--sp-4);min-width:max-content}
.ln.add{color:var(--ok);background:var(--ok-bg)}
.ln.del{color:var(--sev-critical);background:var(--sev-critical-bg)}
.nits{list-style:none;padding:0;margin:0 0 var(--sp-4);background:var(--surface);border:1px solid var(--border);border-radius:var(--r-3);overflow:hidden}
.nits li{display:grid;grid-template-columns:4.5rem minmax(0,1fr) auto;align-items:baseline;gap:var(--sp-4);padding:var(--sp-3) var(--sp-5);font-size:var(--fs-1);overflow-wrap:anywhere}
.nits li+li{border-top:1px solid var(--border)}
.nits .sev{font-size:var(--fs-0)}
.unparsed{margin:0 0 var(--sp-4)}
.unparsed-reason{color:var(--muted);font-size:var(--fs-1)}
.quiet h2{font-size:var(--fs-label);font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-top:var(--sp-7)}
.quiet p,.quiet ul,.quiet ol{max-width:var(--measure);font-size:var(--fs-1)}
footer{margin-top:var(--sp-7);padding-top:var(--sp-4);border-top:1px solid var(--border);color:var(--muted);font-size:var(--fs-0)}
footer p{margin:0 0 var(--sp-2)}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
@media (max-width:56rem){
.hero{grid-template-columns:minmax(0,1fr)}
}
@media (max-width:40rem){
main{padding:var(--sp-5) var(--sp-4) var(--sp-7)}
.meta{gap:var(--sp-1) var(--sp-5)}
.verdict{padding:var(--sp-4) var(--sp-4) var(--sp-4) var(--sp-6)}
.verdict::before{left:var(--sp-3);top:var(--sp-4);bottom:var(--sp-4)}
.verdict-word{font-size:var(--fs-4)}
.finding{padding:0 var(--sp-4) var(--sp-4) var(--sp-6)}
.finding::before{left:var(--sp-3)}
.rows{grid-template-columns:1fr;gap:0}
.rows dt{padding-top:var(--sp-3)}
.rows dt.wide{margin-bottom:0}
.nits li{grid-template-columns:1fr;gap:var(--sp-1);padding:var(--sp-3) var(--sp-4)}
.table-wrap{overflow:visible}
table,tbody,tfoot,tr{display:block}
thead{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
tr{display:flex;flex-wrap:wrap;align-items:baseline;gap:var(--sp-1) var(--sp-4);padding:var(--sp-3) 0;border-bottom:1px solid var(--border)}
tfoot tr{border-bottom:0}
th,td{padding:0;border:0}
tbody th,tfoot th{flex:1 0 100%}
td.num{text-align:left}
td.num::before{content:attr(data-label) " ";color:var(--muted);font-size:var(--fs-0)}
td.num:empty{display:none}
h2{margin-top:var(--sp-6)}
}
"""
CSS_DARK = """\
@media (prefers-color-scheme:dark){
:root{
--bg:#0B1220;--surface:#111A2B;--surface-2:#192438;
--text:#E6EDF7;--muted:#9DAFC6;
--border:rgba(255,255,255,.08);--border-strong:rgba(255,255,255,.16);--shadow:rgba(0,0,0,0);--shadow-2:rgba(0,0,0,0);--hl:rgba(255,255,255,.05);
--accent:#5CD3E8;--accent-bg:rgba(92,211,232,.10);--accent-line:rgba(92,211,232,.35);--focus:#5CD3E8;
--sev-critical:#FB8CA0;--sev-critical-bg:rgba(251,113,133,.11);--sev-critical-line:rgba(251,113,133,.4);
--sev-important:#FBBF55;--sev-important-bg:rgba(251,191,36,.10);--sev-important-line:rgba(251,191,36,.38);
--sev-minor:#7DB4FF;--sev-minor-bg:rgba(96,165,250,.11);--sev-minor-line:rgba(96,165,250,.4);
--sev-nit:#9DAFC6;--sev-nit-bg:rgba(148,163,184,.11);--sev-nit-line:rgba(148,163,184,.35);
--ok:#5BD98A;--ok-bg:rgba(74,222,128,.10);--ok-line:rgba(74,222,128,.38);
}
}
"""
CSS_PRINT = """\
@media print{
:root{
--bg:#FFFFFF;--surface:#FFFFFF;--surface-2:#F0F0F0;
--text:#000000;--muted:#333333;
--border:#BBBBBB;--border-strong:#555555;--shadow:rgba(0,0,0,0);--shadow-2:rgba(0,0,0,0);--hl:rgba(0,0,0,0);
--accent:#000000;--accent-bg:rgba(0,0,0,.04);--accent-line:rgba(0,0,0,.5);--focus:#000000;
--sev-critical:#9B1C12;--sev-critical-bg:rgba(0,0,0,.04);--sev-critical-line:rgba(0,0,0,.5);
--sev-important:#7A3A00;--sev-important-bg:rgba(0,0,0,.04);--sev-important-line:rgba(0,0,0,.5);
--sev-minor:#0B3A8C;--sev-minor-bg:rgba(0,0,0,.04);--sev-minor-line:rgba(0,0,0,.5);
--sev-nit:#333333;--sev-nit-bg:rgba(0,0,0,.04);--sev-nit-line:rgba(0,0,0,.5);
--ok:#0F5224;--ok-bg:rgba(0,0,0,.04);--ok-line:rgba(0,0,0,.5);
}
body{background:var(--bg);color:var(--text);font-size:11pt}
main{max-width:none;padding:0}
.masthead h1{font-size:1.8rem}
.hero{display:block}
.hero>*{margin-bottom:var(--sp-4)}
.finding,.verdict,.banner,.patch,.fix,.overview,.nits li,tr{break-inside:avoid}
.card,.verdict,.finding,.nits,.patch{box-shadow:none}
.diff,.table-wrap{overflow:visible}
.ln{white-space:pre-wrap;min-width:0}
h2{break-after:avoid}
}
"""


def _tone_rules():
    """Per-tone rules from one template, so each tone names only variables defined in :root."""
    tpl = (".verdict.tone-T,.banner.tone-T{background:linear-gradient(var(--V-bg),var(--V-bg)),var(--surface);border-color:var(--V-line)}\n"
           ".verdict.tone-T::before,.banner.tone-T::before,.finding.tone-T::before{background:var(--V)}\n"
           ".ink.tone-T,.sev.tone-T{color:var(--V)}\n"
           ".seg.tone-T{background:var(--V)}\n")
    out = []
    for t, v in [(s, "sev-" + s) for s in SEVERITIES] + [("ok", "ok")]:
        out.append(tpl.replace("-T", "-" + t).replace("--V", "--" + v))
    return "".join(out)


CSS = CSS_BASE.replace("@media (max-width:56rem){", _tone_rules() + "@media (max-width:56rem){", 1) + CSS_DARK + CSS_PRINT

CSP = ("default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
       "base-uri 'none'; form-action 'none'")

OPEN_FENCE = re.compile(r"^ {0,3}(`{3,})([^`]*)$")
CLOSE_FENCE = re.compile(r"^ {0,3}(`{3,})\s*$")
KV = re.compile(r"^\*\*([^:*]+):\*\*\s*(.*)$")
CARD = re.compile(r"^### \[(critical|important|minor|nit)\] (\S.*?)\s*$")
NIT = re.compile(r"^- \[nit\] (\S.*)$", re.I)
NIT_ID = re.compile(r"^(F\d+) (\S.*)$")  # a nit's ID prefix, read only in a file with card IDs
CARD_ID = re.compile(r"F[1-9]\d*")
# The Verify count line in ## Validation (R11). A line is a Verify line when it is a bullet whose text
# starts `Verify:`, `**Verify:**` or `**Verify**:`, any case, colon right after the word (so `- Verify
# Suggested change ...` and `- verified CI` are not), outside a fence. It must then match VERIFY_LINE
# (`Verify:` or `**Verify:**`, any case; `**Verify**:` is reported malformed): four non-negative
# integers in this order and wording, then a non-empty parenthetical (method and trigger, free text:
# not validated). Warned: a Verify line that doesn't match, N != K+D+X, or more than one Verify line.
# No Verify line: no warning (older files).
VERIFY_START = re.compile(r"^\s*[-*]\s+(?:\*\*)?verify(?:\*\*)?:", re.I)
VERIFY_LINE = re.compile(r"^\s*[-*]\s+(?:\*\*Verify:\*\*|Verify:) (\d+) found, (\d+) kept, (\d+) downgraded, (\d+) dropped "
                         r"\((.+)\)\s*$", re.I)
NIT_START = re.compile(r"^- \[nit\]", re.I)
SEV_HEAD = re.compile(r"^### \[(critical|important)\]", re.I)
LIST_ITEM = re.compile(r"^\s*(?:([-*+])|\d+[.)])\s+(.*)$")
BOLD = re.compile(r"\*\*(.+?)\*\*")
# Anchor forms (comment-style.md section 2): path:n, path:a-b (new side), path:-n, path:-a-b (old side),
# path (deleted). The line spec is matched at the END of the value, so the path may hold spaces, `-`,
# digits and `:` (it splits at the last `:`). A path whose own text ends in `:<n>` is unrepresentable,
# a path holding `:<n>` before a space, comma or semicolon is refused as two anchors in one field, and
# a path starting with `/` or holding a backtick is refused.
ANCHOR_LINES = re.compile(r"^(\S.*):(-?)([1-9]\d*)(?:-([1-9]\d*))?$")
ANCHOR_DELETED = re.compile(r"^(\S.*) \(deleted\)$")
ANCHOR_TWO = re.compile(r":-?\d+(?:-\d+)?[\s,;]")
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
# Posted state (R21, R25). A Marker is exactly 12 lowercase hex; Posted is `<platform ref> @ <sha7>`, the ref
# free text (a review-comment id or URL, a note or discussion id) so the posting spike can pin it later.
# Triage lines and nits carry both as a trailing `(Marker <h12>, Posted <ref> @ <sha7>)`, either part
# optional; a final `(...)` that starts `Marker ` or `Posted ` (then an optional `.` or `;`) is read as that
# tail and checked. A nit or triage line with a `(` opening on Marker/Posted (any case) but no such tail is a near miss
# and warns, as does a Not re-raised/Fixed line with an F-ID in any other form (e.g. a bold label).
MARKER_RE = re.compile(r"[0-9a-f]{12}")
POSTED_RE = re.compile(r"\S.*? @ [0-9a-f]{7,40}")
TAIL = re.compile(r"\(((?:Marker|Posted) [^()]*)\)\s*[.;]?\s*$")
STATE_WORD = re.compile(r"\(\W*(?:marker|posted)\b", re.I)  # a near-miss tail; a title saying "posted" is fine
CODE_SPAN = re.compile(r"`[^`\n]+`")  # cut before the near-miss match only, so `get(marker)` is code, not a tail
SPAN_TAIL = re.compile(r"\((?:marker|posted)\s", re.I)  # a span holding a tail-like "(Marker " is not cut
COLLAPSED_NIT = re.compile(r"^[1-9]\d* more not shown:")  # the nit cap's summary line: shown, never counted
COLLAPSED_LOOSE = re.compile(r"^\S+\s+more\s+not\s+shown\b", re.I)  # a near miss of it: warned, counted
DROPPED = re.compile(r"^\s*[-*]\s+Dropped (F\d+):")  # a Verify drop in Validation: its ID counts toward Last ID
TAIL_BODY = re.compile(r"(?:Marker (?P<m>[^,\s]+)(?:, Posted (?P<p>.+))?|Posted (?P<p2>.+))")
TRIAGE = re.compile(r"^\s*[-*]\s+(?:Not re-raised|Fixed):\s+(F\d+)\b(.*)$")
TRIAGE_LOOSE = re.compile(r"^\s*[-*]\s+\W*(?:not re-raised|fixed)\b.*\bF\d+\b", re.I)
LAST_ID = re.compile(r"^\s*[-*]\s+Last ID:\s*F(\d+)\s*$")
MARKER_SOURCE = re.compile(r"canonical|fresh-[0-9a-f]{7}")
MARKER_KEY = re.compile(r"[a-z0-9-]{1,64}")  # the isolated-checkout <key>: mr-<id> or branch-<slug>


def e(s):
    return html.escape(s, quote=True)


def inline(text):
    """Escape, then render `code` and **bold** only. No links, no raw HTML."""
    out = []
    for i, part in enumerate(re.split(r"(`[^`\n]+`)", text)):
        if i % 2:
            out.append("<code>%s</code>" % e(part[1:-1]))
        else:
            out.append(BOLD.sub(lambda m: "<strong>%s</strong>" % m.group(1), e(part)))
    return "".join(out)


def fence_step(line, fence):
    """Track a ``` fence: return the opener length while inside one, else None."""
    if fence is None:
        m = OPEN_FENCE.match(line)
        return len(m.group(1)) if m else None
    m = CLOSE_FENCE.match(line)
    return None if m and len(m.group(1)) >= fence else fence


def blocks(lines):
    """Generic fallback: paragraphs, lists, fenced code. Returns (html, unclosed_fence)."""
    out, para, items = [], [], []
    list_tag = None
    code = None

    def flush():
        nonlocal para, items, list_tag
        if para:
            out.append("<p>%s</p>" % inline(" ".join(s.strip() for s in para)))
        if items:
            out.append("<%s>%s</%s>" % (list_tag, "".join("<li>%s</li>" % inline(i) for i in items), list_tag))
        para, items, list_tag = [], [], None

    fence = None
    for line in lines:
        was = fence
        fence = fence_step(line, fence)
        if was is None and fence is not None:
            flush()
            code = []
        elif was is not None:
            if fence is None:
                out.append("<pre tabindex=\"0\"><code>%s</code></pre>" % e("\n".join(code)))
                code = None
            else:
                code.append(line)
        elif not line.strip():
            flush()
        else:
            m = LIST_ITEM.match(line)
            if m:
                tag = "ul" if m.group(1) else "ol"
                if tag != list_tag:
                    flush()
                    list_tag = tag
                items.append(m.group(2))
            elif items and line.startswith((" ", "\t")):
                items[-1] += " " + line.strip()
            else:
                if items:
                    flush()
                para.append(line)
    flush()
    if code is not None:
        out.append("<pre tabindex=\"0\"><code>%s</code></pre>" % e("\n".join(code)))
    return "\n".join(out), fence is not None


def split_lines(text):
    """Normalise CRLF/CR to LF, then split on LF only (U+2028, U+0085, \\x0b, \\x0c are not breaks)."""
    return text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").split("\n")


def count_headings(lines):
    """-> (card-looking headings outside code fences, those that look critical/important).

    Inside the three findings sections (and unknown sections, or before any section) every `### `
    counts; in the other known sections (Validation, Prior findings triaged, Verdict) only a
    `### [` heading counts, so plain sub-headings there do not make a false "N of M" banner."""
    total = blocking = 0
    fence = None
    quiet = False  # inside a known non-findings section
    findings = {h.lower() for h, a in SECTIONS if a}
    quiet_names = {h.lower() for h, a in SECTIONS if not a}
    for line in lines:
        was = fence
        fence = fence_step(line, fence)
        if was is None and fence is None:
            if line.startswith("## "):
                name = line[3:].strip().lower()
                quiet = name in quiet_names and name not in findings
            elif line.startswith("### ") and (not quiet or line.startswith("### [")):
                total += 1
                blocking += bool(SEV_HEAD.match(line))
    return total, blocking


def split_document(lines, warn):
    """-> (title, header dict, [(section heading, lines)], [(raw text, reason)] for unparsed preamble)."""
    title, header, sections = None, {}, []
    pre_text, pre_dup = [], []
    cur = None
    fence = None
    in_card = False
    for line in lines:
        was = fence
        fence = fence_step(line, fence)
        if was is None and fence is None and line.startswith("## "):
            cur = (line[3:].strip(), [])
            sections.append(cur)
        elif cur is not None:
            cur[1].append(line)
        elif was is None and fence is None and title is None and line.startswith("# "):
            title = line[2:].strip()
            if title.lower().startswith("review:"):
                title = title[7:].strip()
        elif was is not None or fence is not None or line.strip():
            if was is None and fence is None and line.startswith("### "):
                in_card = True
            m = KV.match(line) if was is None and fence is None and not in_card else None
            if m and m.group(1).strip() in HEADER_KEYS + OPTIONAL_HEADER_KEYS:
                k = m.group(1).strip()
                if k in header:
                    pre_dup.append(line)
                    warn("duplicate header key %r not used" % k)
                else:
                    header[k] = m.group(2).strip()
            else:
                pre_text.append(line)
    unparsed = []
    if "".join(pre_text).strip():
        unparsed.append(("\n".join(pre_text).strip("\n"), "text before the first section that is not a header line"))
        warn("unrecognised text before the first section")
    if pre_dup:
        unparsed.append(("\n".join(pre_dup), "duplicate header key (only the first is used)"))
    return title, header, sections, unparsed


def parse_card(heading, body):
    """-> (card dict, None) or (None, reason)."""
    m = CARD.match(heading)
    if not m:
        return None, "heading is not `### [severity] Title`"
    fields, order, cur, fence = {}, [], None, None
    for line in body:
        was = fence
        fence = fence_step(line, fence)
        km = KV.match(line) if was is None and fence is None else None
        if km:
            cur = km.group(1).strip()
            if cur in fields:
                return None, "duplicate field %s" % cur
            fields[cur] = [km.group(2)] if km.group(2).strip() else []
            order.append(cur)
        elif cur is not None:
            fields[cur].append(line)
        elif line.strip():
            return None, "text before the first field"
    if fence is not None:
        return None, "unclosed code fence"
    axis = " ".join(fields.get("Axis", [])).strip()
    conf = " ".join(fields.get("Confidence", [])).strip()
    if axis not in AXES:
        return None, "Axis must be one of: " + ", ".join(AXES)
    if conf not in CONFIDENCE:
        return None, "Confidence must be one of: " + ", ".join(CONFIDENCE)
    if not "".join(fields.get("What", [])).strip():
        return None, "missing What"
    return {"severity": m.group(1), "title": m.group(2), "axis": axis, "confidence": conf,
            "id": " ".join(fields.get("ID", [])).strip() or None,
            "in_diff": " ".join(fields["In diff"]).strip() if "In diff" in fields else None,
            "fields": fields, "order": order}, None


def parse_findings(lines, section_axis, warn):
    """-> (cards, nit lines, unparsed [(raw text, reason)])."""
    cards, nits, unparsed, stray = [], [], [], []
    cur, fence = None, None

    def finish():
        nonlocal cur
        if cur is None:
            return
        card, why = parse_card(cur[0], cur[1])
        if card:
            cards.append(card)
        else:
            unparsed.append(("\n".join([cur[0]] + cur[1]).rstrip(), why))
        cur = None

    for line in lines:
        was = fence
        fence = fence_step(line, fence)
        if was is None and fence is None and line.startswith("### "):
            finish()
            cur = (line, [])
        elif was is None and fence is None and NIT.match(line):
            finish()
            if not line.startswith("- [nit] "):
                warn("nit line %r accepted case-insensitively; write it as '- [nit] ...'" % line[:60])
            text_ = NIT.match(line).group(1)
            collapsed = bool(COLLAPSED_NIT.match(text_))
            if not collapsed and COLLAPSED_LOOSE.match(text_):
                warn("nit %r looks like the nit cap's summary line but is not '- [nit] N more not shown: "
                     "<titles>' (N from 1); counted as a nit" % line[:60])
            nits.append({"text": text_, "id": None, "axis": section_axis, "collapsed": collapsed})
        elif was is None and fence is None and NIT_START.match(line):
            finish()
            unparsed.append((line, "malformed nit line (expected `- [nit] text`)"))
        elif cur is not None:
            cur[1].append(line)
        elif line.strip() and line.strip() != "None.":
            if line.startswith("- ["):
                unparsed.append((line, "malformed nit line (expected `- [nit] text`)"))
            else:
                stray.append(line)
    finish()
    if stray:
        unparsed.append(("\n".join(stray), "text outside any finding card"))
    for c in cards:
        if c["axis"] != section_axis:
            warn("card %r has Axis %s under the %s section" % (c["title"], c["axis"], section_axis))
        for k in ("Why", "Fix"):
            if c["severity"] != "nit" and not "".join(c["fields"].get(k, [])).strip():
                warn("card %r has no %s" % (c["title"], k))
    return cards, nits, unparsed


def parse_anchor(text):
    """-> {"path", "side": new|old|file, "start", "end"} or None when malformed. A reversed range
    (b < a) still parses; the caller flags it."""
    t = text.strip().strip("`").strip()
    m = ANCHOR_DELETED.match(t) or ANCHOR_LINES.match(t)
    if not m or m.group(1).startswith("/") or "`" in m.group(1) or ANCHOR_TWO.search(m.group(1) + " "):
        return None
    if m.re is ANCHOR_DELETED:
        return {"path": m.group(1), "side": "file", "start": None, "end": None}
    a = int(m.group(3))
    return {"path": m.group(1), "side": "old" if m.group(2) else "new", "start": a,
            "end": int(m.group(4)) if m.group(4) else a}


def _diff_path(raw):
    """A `--- a/x` / `+++ b/x` header path -> repo-relative path, or None for /dev/null."""
    raw = raw.rstrip("\t")  # git appends a tab when the path has a space
    if raw.startswith('"') and raw.endswith('"'):  # C-quoted: escapes and octal UTF-8 bytes
        raw = codecs.escape_decode(raw[1:-1].encode("utf-8"))[0].decode("utf-8", "replace")
    if raw == "/dev/null":
        return None
    return raw[2:] if raw[:2] in ("a/", "b/") else raw


def anchor_in_diff(diff_text, anchor, repo=None):
    """-> "yes", "no", "nofile" (the path matches no file with hunks in the diff), or None (malformed or
    reversed anchor), from `git diff -U0` text. The input must be `git diff` output with `diff --git`
    headers; other diff formats read as nofile.

    A file is keyed by its head-side path (`+++`), or its `---` path when deleted; an anchor names that
    path on both sides, so an old-side anchor on a renamed file uses the new name. New-side anchors check
    the `+c,d` ranges, old-side ones `-a,b`; yes only if every line lies inside one hunk (a count of 0
    covers no lines, a missing count is 1). File level is no. `---`/`+++` are read only in a file header
    (after `diff --git`, before the first `@@`). With `repo`, a leading `<repo>/` is stripped and only
    that exact path matches; without it, the path matches as written or minus its first segment."""
    a = parse_anchor(anchor)
    if a is None or (a["start"] is not None and a["end"] < a["start"]):
        return None
    if a["side"] == "file":
        return "no"
    if repo:
        want = {a["path"][len(repo) + 1:] if a["path"].startswith(repo + "/") else a["path"]}
    else:
        want = {a["path"], a["path"].split("/", 1)[-1]}
    old = new = None
    header = found = False
    for line in split_lines(diff_text):
        if line.startswith("diff --git "):
            old = new = None
            header = True
        elif header and line.startswith("--- "):
            old = _diff_path(line[4:])
        elif header and line.startswith("+++ "):
            new = _diff_path(line[4:])
        else:
            m = HUNK.match(line)
            if not m:
                continue
            header = False
            if (new or old) not in want:
                continue
            found = True
            start, count = (m.group(1), m.group(2)) if a["side"] == "old" else (m.group(3), m.group(4))
            start, count = int(start), 1 if count is None else int(count)
            if count and start <= a["start"] and a["end"] <= start + count - 1:
                return "yes"
    return "no" if found else "nofile"


def in_diff_report(text, diff_text, repo=None):
    """-> one `<ID or title>\t<anchor>\tyes|no|nofile|malformed` line per card with an Anchor, in file order."""
    _, _, sections, _ = split_document(split_lines(text), lambda _m: None)
    axis_of = {h.lower(): a for h, a in SECTIONS[:3]}
    out = []
    for heading, slines in sections:
        axis = axis_of.get(heading.strip().lower())
        if axis is None:
            continue
        for c in parse_findings(slines, axis, lambda _m: None)[0]:
            raw = " ".join(c["fields"].get("Anchor", [])).strip()
            if raw:
                v = anchor_in_diff(diff_text, raw, repo) or "malformed"
                out.append("\t".join(x.replace("\t", " ") for x in (c["id"] or c["title"], raw.strip("`"), v)))
    return out


def marker(key, source, fid):
    """The posting marker h12 = sha256("<key>|<source>|<ID>")[:12] (D7), computed once at first post."""
    if not MARKER_KEY.fullmatch(key) or not MARKER_SOURCE.fullmatch(source) or not CARD_ID.fullmatch(fid):
        raise ValueError("expected a key of [a-z0-9-] (mr-<id> or branch-<name>), source canonical or fresh-<sha7>, and an ID F<n>")
    return hashlib.sha256(("%s|%s|%s" % (key, source, fid)).encode("utf-8")).hexdigest()[:12]


def parse_tail(text):
    """-> (marker or None, posted or None, problem or None) from a trailing `(Marker .., Posted ..)`."""
    m = TAIL.search(text)
    if not m:
        return None, None, None
    b = TAIL_BODY.fullmatch(m.group(1).strip())
    if not b:
        return None, None, "malformed (Marker <h12>, Posted <ref> @ <sha7>) tail %r" % m.group(0)[:80]
    return b.group("m"), b.group("p") or b.group("p2"), None


def state_problems(what, mk, posted):
    out = []
    if mk is not None and not MARKER_RE.fullmatch(mk):
        out.append("%s has a malformed Marker %r (expected 12 lowercase hex)" % (what, mk))
    if posted is not None and not POSTED_RE.fullmatch(posted):
        out.append("%s has a malformed Posted %r (expected '<platform ref> @ <sha7>')" % (what, posted))
    return out


def _field(card, k):
    return " ".join(card["fields"][k]).strip() if k in card["fields"] else None


def scan_state(by_name, cards, nits):
    """Shared by render() and posted_state(), so both read the same IDs. `by_name` maps a lower-case section
    name to its lines. Sets each nit's "id" (and strips it from "text") when its text starts `F<n> ` and the
    nit carries a posted-state tail or the file has a card ID, a Last ID line or a triage ID. -> (triage
    [(ID, rest of line)], Last ID or None, [malformed triage lines])."""
    triage, loose, last = [], [], None
    for name in ("prior findings triaged", "validation"):
        fence = None
        for ln in by_name.get(name, []):
            inside, fence = fence, fence_step(ln, fence)
            if inside is not None or fence is not None:
                continue
            if name == "validation":
                lm = LAST_ID.match(ln)
                if lm and last is None:
                    last = int(lm.group(1))
                continue
            t = TRIAGE.match(ln)
            if t:
                triage.append((t.group(1), t.group(2)))
            elif TRIAGE_LOOSE.match(ln):
                loose.append(ln.strip())
    gate = any(c["id"] for c in cards) or last is not None or bool(triage)
    for n in nits:
        idm = NIT_ID.match(n["text"])
        if idm and (gate or TAIL.search(idm.group(2))):
            n["id"], n["text"] = idm.group(1), idm.group(2)
    return triage, last, loose


def _cut_code(text):
    """`text` minus inline code spans, except a span right after `(` or one holding `(Marker `/`(Posted `,
    which could be a tail wrapped in backticks."""
    return CODE_SPAN.sub(lambda m: m.group(0) if text[m.start() - 1:m.start()] == "(" or SPAN_TAIL.search(m.group(0))
                         else "", text)


def tail_problems(nits, triage, loose):
    """-> the posted-state problems of nit and triage lines (scan_state output): malformed triage lines,
    malformed or near-miss tails and bad Marker/Posted values. Shared by render() and previous_report()."""
    out = ["triage line %r is not in the form '- Not re-raised: F<n> ...' or '- Fixed: F<n> ...'" % ln[:60]
           for ln in loose]
    tails = [("nit %r" % n["text"][:40], n["text"]) for n in nits]
    tails += [("triage line %s" % fid, rest) for fid, rest in triage]
    for what, text_ in tails:
        mk, posted, bad = parse_tail(text_)
        if bad:
            out.append("%s has a %s" % (what, bad))
        elif mk is None and posted is None and STATE_WORD.search(_cut_code(text_)):
            out.append("%s has a Marker/Posted near-miss: a '(' naming Marker/Posted but no "
                       "'(Marker <h12>, Posted <ref> @ <sha7>)' tail at its end" % what)
        out += state_problems(what, mk, posted)
    return out


def posted_state(text):
    """-> ({ID number: (ID, Marker, Posted)} over cards, nits and Not re-raised/Fixed triage lines, Last ID or
    None, [(ID number or None, tail problem, the line's posted-state text)]). Sections are matched by name, any case; nit IDs are read as in render() (scan_state)."""
    _, _, sections, _ = split_document(split_lines(text), lambda _m: None)
    axis_of = {h.lower(): a for h, a in SECTIONS[:3]}
    by_name, cards, nits = {}, [], []
    for heading, slines in sections:
        name = heading.strip().lower()
        by_name.setdefault(name, []).extend(slines)
        if name in axis_of:
            c, n, _ = parse_findings(slines, axis_of[name], lambda _m: None)
            cards += c
            nits += n
    triage, last, loose = scan_state(by_name, cards, nits)
    items = [(fid,) + parse_tail(rest)[:2] for fid, rest in triage]
    items += [(c["id"], _field(c, "Marker"), _field(c, "Posted")) for c in cards if c["id"]]
    items += [(n["id"],) + parse_tail(n["text"])[:2] for n in nits if n["id"]]
    ids = {}
    for fid, mk, posted in items:
        if not CARD_ID.fullmatch(fid):
            continue
        prev = ids.get(int(fid[1:]), (fid, None, None))
        ids[int(fid[1:])] = (fid, prev[1] if prev[1] is not None else mk, prev[2] if prev[2] is not None else posted)
    # tail problems one line at a time, in tail_problems() order, each with its ID number and its tail text
    problems = []
    for ln in loose:
        m = re.search(r"\bF([1-9]\d*)\b", ln)
        problems += [(int(m.group(1)) if m else None, msg, _tail_key(ln)) for msg in tail_problems([], [], [ln])]
    for n in nits:
        num = int(n["id"][1:]) if n["id"] and CARD_ID.fullmatch(n["id"]) else None
        problems += [(num, msg, _tail_key(n["text"])) for msg in tail_problems([n], [], [])]
    for fid, rest in triage:
        num = int(fid[1:]) if CARD_ID.fullmatch(fid) else None
        problems += [(num, msg, _tail_key(rest)) for msg in tail_problems([], [(fid, rest)], [])]
    return ids, last, problems


def _tail_key(text):
    """The posted-state part of a line: its last `(...)` naming Marker/Posted, else the whole line."""
    groups = [g for g in re.findall(r"\([^()]*\)", text) if re.search(r"marker|posted", g, re.I)]
    return (groups[-1] if groups else text).strip()


UNREPAIRABLE = ("unrepairable: %s has a malformed or unreadable Marker/Posted in the old file; mark it "
                "do-not-post and ask the user")


def previous_report(old_text, new_text):
    """-> problems of a canonical rewrite against the file it replaces (R25): a prior ID with a Marker or
    Posted value that is gone or whose value changed, a lower Last ID or max ID, and an ID that the old file
    had already used up (at or below its Last ID/max but absent from it) appearing again, plus every malformed
    or near-miss posted-state line in either file (prefixed "old file: "/"new file: "). An old ID with a
    malformed or unreadable Marker/Posted is unrepairable: it gets an `unrepairable:` line, its values are not
    compared on its malformed half, a new-file line carrying its old tail verbatim is folded into that line,
    and dropping it is still reported. Unposted IDs (no Marker, no Posted) may disappear."""
    old, old_last, old_bad = posted_state(old_text)
    new, new_last, new_bad = posted_state(new_text)
    bad_ids = {num for num, _, _ in old_bad if num is not None}
    bad_ids |= {num for num, (_, mk, posted) in old.items() if state_problems("", mk, posted)}
    old_keys = {(num, key) for num, _, key in old_bad}
    present = set(new) | {num for num, _, _ in new_bad if num is not None}  # a loose new line still names its ID
    # near misses in either file, so a render warning that went unread can't hide a posted ID
    out = ["old file: " + m for _, m, _ in old_bad]
    out += ["new file: " + m for num, m, key in new_bad if not (num in bad_ids and (num, key) in old_keys)]
    for num in sorted(bad_ids):
        fid = old[num][0] if num in old else "F%d" % num
        out.append(UNREPAIRABLE % fid)
        if num not in present:
            out.append("prior ID %s is missing from the new file (dropped); keep it, with its Marker/Posted "
                       "text carried verbatim" % fid)
    for num, (fid, mk, posted) in old.items():
        if mk is None and posted is None:
            continue
        if num not in new:
            if num not in bad_ids:  # an unrepairable drop is reported above
                out.append("prior ID %s has a Marker or Posted value but is missing from the new file (dropped); "
                           "keep it as a card, nit or Not re-raised/Fixed line with its values" % fid)
            continue
        for label, was, now in (("Marker", mk, new[num][1]), ("Posted", posted, new[num][2])):
            if num in bad_ids and state_problems("", *((was, None) if label == "Marker" else (None, was))):
                continue  # only the malformed half of an unrepairable ID goes uncompared
            if was is not None and was != now:
                out.append("prior ID %s %s changed from %r to %r; carry it verbatim" % (fid, label, was, now))
    old_top = max(max(old, default=0), old_last or 0)  # the highest ID ever used, as far as each file shows
    new_top = max(max(new, default=0), new_last or 0)
    if old_last is not None and new_last is None:
        out.append("Last ID line missing (the old file has - Last ID: F%d)" % old_last)
    elif old_last is not None and new_last < old_last:
        out.append("Last ID F%d is lower than the old Last ID F%d" % (new_last, old_last))
    elif new_top < old_top:
        out.append("max ID F%d is lower than the old max ID F%d" % (new_top, old_top))
    for num, (fid, _, _) in sorted(new.items()):
        if num <= old_top and num not in old and num not in bad_ids:
            out.append("ID %s reuses a number the old file had already used up (at or below F%d, not in it); "
                       "give the finding a new ID above it" % (fid, old_top))
    return out


def norm_verdict(s):
    s = re.sub(r"[*_`]", "", s).strip().rstrip(".").strip().lower()
    for v in VERDICTS:
        if v.lower() == s:
            return v
    return None


def banner(tone, glyph, lead, body):
    return ('<div class="banner tone-%s" role="alert"><p><span class="lead ink tone-%s">'
            '<span aria-hidden="true">%s</span> %s</span></p><p>%s</p></div>' % (tone, tone, glyph, e(lead), body))


def sevlabel(sev):
    """Severity as a glyph plus the word, never colour alone."""
    return '<span class="sev tone-%s"><span aria-hidden="true">%s</span> %s</span>' % (
        sev, GLYPH[sev], sev.capitalize())


def render_patch(lines):
    """The Suggested change field: prose and each fenced block, in source order. Every fence is its
    own diff block under the fixed label; the label appears only when there is a diff body."""
    out, text, diff, fence = [], [], None, None

    def flush_text():
        nonlocal text
        if "".join(text).strip():
            out.append(blocks(text)[0])
        text = []

    def flush_diff():
        nonlocal diff
        if diff is not None and "".join(diff).strip():
            rows = []
            for ln in diff:
                cls = "add" if ln.startswith("+") else "del" if ln.startswith("-") else "ctx"
                rows.append('<span class="ln %s">%s</span>' % (cls, e(ln) or " "))
            out.append('<div class="patch"><div class="patch-bar"><span aria-hidden="true">&#177;</span> %s</div>'
                       '<div class="diff" tabindex="0" role="region" aria-label="%s">%s</div></div>'
                       % (PATCH_LABEL, PATCH_LABEL, "".join(rows)))
        diff = None

    for line in lines:
        was = fence
        fence = fence_step(line, fence)
        if was is None and fence is not None:
            flush_text()
            diff = []
        elif was is not None and fence is not None:
            diff.append(line)
        elif was is not None:
            flush_diff()
        elif line.strip().strip("*").strip().lower() != PATCH_LABEL.lower():
            text.append(line)
    flush_diff()  # unclosed fence: the rest is still shown as a diff block
    flush_text()
    return "".join(out)


def render_card(card, sha):
    sev = card["severity"]
    f = card["fields"]
    rows = []
    for k in card["order"]:
        if k in ("Axis", "Confidence", "Anchor", "ID", "In diff"):  # shown in the card meta
            continue
        if k == "Suggested change":
            if "".join(f[k]).strip():
                rows.append('<dt class="wide">Suggested change</dt><dd class="wide">%s</dd>' % render_patch(f[k]))
            continue
        lines = f[k]
        if k == "Evidence":
            lines = [re.sub(r"^\s*(?:>\s?)+", "", ln) for ln in lines]
            if not any(OPEN_FENCE.match(ln) for ln in lines):  # one quoted line per paragraph
                lines = [x for ln in lines for x in (ln, "")]
        rows.append('<dt>%s</dt><dd%s>%s</dd>' % (e(k), ' class="quote"' if k == "Evidence" else "",
                                                  blocks(lines)[0]))
    anchor = " ".join(f.get("Anchor", [])).strip().strip("`")
    conf = card["confidence"]
    return (
        '<article class="finding tone-%s"><header class="f-head"><h3>%s</h3><p class="f-meta">%s%s%s<span class="tag %s">%s</span>%s%s</p></header>'
        '<dl class="rows">%s</dl>'
        '<p class="f-foot">Axis: %s &middot; Head SHA: <code>%s</code></p></article>'
        % (sev, inline(card["title"]), '<span class="tag">%s</span>' % e(card["id"]) if card["id"] else "",
           sevlabel(sev),
           '<span class="tag blocking">Blocking</span>' if sev in BLOCKING else '<span class="tag">Non-blocking</span>',
           conf, ("&#10003; " if conf == "confirmed" else "? ") + conf.capitalize(),
           '<span class="tag">In diff: %s</span>' % e(card["in_diff"]) if card["in_diff"] is not None else "",
           '<code class="anchor">%s</code>' % e(anchor) if anchor else "",
           "".join(rows), card["axis"], e(sha)))


def render_overview(counts):
    """Stacked severity bar (flex-grow = the integer count) plus the severity x axis table."""
    sev_tot = {s: sum(counts[(s, a)] for a in AXES) for s in SEVERITIES}
    total = sum(sev_tot.values())
    blocking = sum(sev_tot[s] for s in BLOCKING)
    segs = "".join('<span class="seg tone-%s" style="flex-grow:%d"></span>' % (s, sev_tot[s])
                   for s in SEVERITIES if sev_tot[s])
    label = ", ".join("%s %d" % (s.capitalize(), sev_tot[s]) for s in SEVERITIES)
    head = "".join('<th scope="col" class="num">%s</th>' % a.capitalize() for a in AXES)
    body, col_tot = [], {a: 0 for a in AXES}
    for s in SEVERITIES:
        cells = "".join('<td class="num" data-label="%s">%d</td>' % (a.capitalize(), counts[(s, a)]) for a in AXES)
        for a in AXES:
            col_tot[a] += counts[(s, a)]
        body.append('<tr><th scope="row">%s</th>%s'
                    '<td class="num" data-label="Total">%d</td><td class="num" data-label="Blocking">%s</td></tr>'
                    % (sevlabel(s), cells, sev_tot[s], "Yes" if s in BLOCKING else "No"))
    foot = "".join('<td class="num" data-label="%s">%d</td>' % (a.capitalize(), col_tot[a]) for a in AXES)
    return ('<section class="overview card"><h2>Severity overview</h2>'
            '<p class="stat"><strong>%d</strong><span>findings</span><strong>%d</strong><span>blocking</span></p>'
            '<div class="bar" role="img" aria-label="Findings by severity: %s">%s</div>'
            '<div class="table-wrap" tabindex="0" role="region" aria-label="Findings by severity and axis">'
            '<table><caption>Findings by severity and axis (counted from parsed cards)</caption>'
            '<thead><tr><th scope="col">Severity</th>%s<th scope="col" class="num">Total</th>'
            '<th scope="col" class="num">Blocking</th></tr></thead><tbody>%s</tbody>'
            '<tfoot><tr><th scope="row">Total</th>%s<td class="num" data-label="Total">%d</td><td class="num"></td></tr></tfoot>'
            '</table></div></section>' % (total, blocking, label, segs, head, "".join(body), foot, total))


def render(text, name):
    """-> (html text, [warnings])."""
    warnings = []
    warn = warnings.append
    lines = split_lines(text)
    title, header, sections, unparsed = split_document(lines, warn)
    total, total_blocking = count_headings(lines)
    problems = []  # structure problems shown in one visible banner (and on stderr)

    def problem(msg):
        problems.append(msg)
        warn(msg)

    if title is None:
        warn("missing '# Review: <title>' line")
    for k in HEADER_KEYS:
        if k not in header:
            warn("missing header key %s" % k)
    known = [s for s, _ in SECTIONS]
    canon = {k.lower(): k for k in known}
    by_name, named, extra = {}, [], []  # named: (canonical name or None, heading, lines)
    for heading, slines in sections:
        c = canon.get(heading.strip().lower())
        named.append((c, heading, slines))
        if c is None:
            problem("unknown section %r (shown below as escaped text, not parsed)" % heading)
            extra.append(heading)
            continue
        if heading != c:
            problem("section %r should be named %r" % (heading, c))
        if c in by_name:
            problem("duplicate section %r" % c)
            by_name[c].extend(slines)
        else:
            by_name[c] = list(slines)
    for s_ in known:
        if s_ not in by_name:
            problem("missing section %r" % s_)
    seq = [c for c, _, _ in named if c]
    if seq != sorted(seq, key=known.index):
        problem("sections are out of order")
    structured = bool(by_name) or any(k in header for k in HEADER_KEYS)
    if "Mode" in header and header["Mode"] not in MODES:
        problem("header Mode %r is not one of: %s" % (header["Mode"], ", ".join(MODES)))
    if "Since" in header and not SHA_RE.fullmatch(header["Since"].strip("`")):  # backticks allowed, as on Head SHA
        problem("header Since %r is not a 7-40 character lowercase hex SHA" % header["Since"])
    if "Ticket" in header and not TICKET_STATE_RE.search(header["Ticket"]):
        warn("header Ticket %r gives no key a state; write KEY (fetched) or KEY (not fetched: <reason>)"
             % header["Ticket"])  # soft: stderr only, no banner

    fence, vlines = None, []
    for ln in by_name.get("Validation", []):
        inside, fence = fence, fence_step(ln, fence)
        if inside is None and fence is None and VERIFY_START.match(ln):
            vlines.append(ln.strip())
    if len(vlines) > 1:
        problem("Verify line appears %d times in Validation (expected exactly one)" % len(vlines))
    for vl in vlines:
        vm = VERIFY_LINE.match(vl)
        if not vm:
            problem("malformed Verify line %r (expected '- Verify: N found, K kept, D downgraded, X dropped "
                    "(<method>; trigger: <threshold>)')" % vl[:80])
            continue
        n, k, d, x = (int(g) for g in vm.groups()[:4])
        if n != k + d + x:
            problem("Verify line says %d found but %d+%d+%d = %d (kept+downgraded+dropped)" % (n, k, d, x, k + d + x))

    cards, nits = [], []
    for heading, axis in SECTIONS[:3]:
        if heading not in by_name:
            continue
        c, n, u = parse_findings(by_name[heading], axis, warn)
        cards += [dict(x, seq=len(cards) + i) for i, x in enumerate(c)]
        nits += n
        unparsed += u
    parsed = len(cards)
    # nit IDs: see scan_state. A file without card IDs, Last ID, triage IDs or tails keeps nit text verbatim.
    triage, last_id, loose = scan_state({k.lower(): v for k, v in by_name.items()}, cards, nits)
    used = [int(x["id"][1:]) for x in cards + nits if x["id"] and CARD_ID.fullmatch(x["id"])]
    used += [int(fid[1:]) for fid, _ in triage if CARD_ID.fullmatch(fid)]
    used += [int(m.group(1)[1:]) for ln in by_name.get("Validation", []) for m in [DROPPED.match(ln)]
             if m and CARD_ID.fullmatch(m.group(1))]
    if last_id is not None and used and max(used) > last_id:
        problem("Last ID F%d is lower than the highest ID used in the file, F%d; raise it so no ID is reused"
                % (last_id, max(used)))
    for c in cards:
        if c["in_diff"] is not None and c["in_diff"] not in IN_DIFF:
            problem("card %r has In diff %r (expected yes or no)" % (c["title"], c["in_diff"]))
        raw = " ".join(c["fields"].get("Anchor", [])).strip()
        if raw:
            a = parse_anchor(raw)
            if a is None:
                problem("card %r has a malformed Anchor %r (expected path:n, path:a-b, path:-n, path:-a-b "
                        "or path (deleted))" % (c["title"], raw))
            elif a["start"] is not None and a["end"] < a["start"]:
                problem("card %r has a reversed Anchor range %r (b < a)" % (c["title"], raw))
        if c["id"] and not CARD_ID.fullmatch(c["id"]):
            problem("card %r has ID %r (expected F<n>, e.g. F1)" % (c["title"], c["id"]))
        for msg in state_problems("card %r" % c["title"], _field(c, "Marker"), _field(c, "Posted")):
            problem(msg)
    for msg in tail_problems(nits, triage, loose):
        problem(msg)
    seen = {}  # ID number (or raw text) -> [first form, uses]; dicts keep insertion order: deterministic
    for x in cards + nits:
        if x["id"]:
            key = int(x["id"][1:]) if re.fullmatch(r"F\d+", x["id"]) else x["id"]
            seen.setdefault(key, [x["id"], 0])[1] += 1
    for fid, uses in seen.values():
        if uses > 1:
            problem("duplicate ID %s (used %d times)" % (fid, uses))

    counts = {(s, a): 0 for s in SEVERITIES for a in AXES}
    for c in cards:
        counts[(c["severity"], c["axis"])] += 1
    for n in nits:
        counts[("nit", n["axis"])] += not n["collapsed"]
    blocking = sum(counts[(s, a)] for s in BLOCKING for a in AXES)
    hidden_blocking = max(0, total_blocking - sum(1 for c in cards if c["severity"] in BLOCKING))

    sha = header.get("Head SHA") or "unknown"
    vsec = by_name.get("Verdict", [])
    strengths = next((ln.strip() for ln in vsec if re.sub(r"[*_]", "", ln).strip().startswith("Strengths:")), None)
    vsec_first = next((ln for ln in vsec if ln.strip() and ln.strip() != strengths), "")
    verdict = norm_verdict(header.get("Verdict", "")) or (None if "Verdict" in header else norm_verdict(vsec_first))
    banners = []
    if not structured:
        banners.append(banner("critical", "✖", "Not a structured review — nothing was parsed",
                              "No title section, header key or known section was found, so there are no counts "
                              "and no verdict. The file content is shown below as escaped text."))
        warn("not a structured review: nothing parsed")
        verdict = None
    if unparsed:
        problems.append("%d block(s) of text were not parsed (shown under Unparsed text)" % len(unparsed))
    if problems and structured:
        banners.append(banner("important", "▲", "Review file structure problems",
                              "; ".join(e(x) for x in problems) + ". Fix the review file."))
    if parsed < total:
        banners.append(banner("critical", "✖", "%d of %d cards parsed" % (parsed, total),
                              "Cards that did not parse are shown below as escaped text and are not counted."))
    if not structured:
        pass
    elif verdict is None:
        shown = header.get("Verdict") or vsec_first or "(none)"
        banners.append(banner("important", "▲", "Verdict not recognised",
                              "Expected one of %s; found %s." % (", ".join(VERDICTS), e(shown))))
        warn("verdict not recognised: %r" % shown)
    else:
        bad = None
        if verdict in ("Approve", "Approve with changes") and (blocking or hidden_blocking):
            bad = "%s, but %d critical or important finding(s) are blocking." % (verdict, blocking)
            if hidden_blocking:
                bad = "%s, but %d critical or important card(s) were found that are NOT counted in the table " \
                      "(they are in a section or form the parser does not read)" % (verdict, hidden_blocking)
                if blocking:
                    bad += "; %d more are counted" % blocking
                bad += "."
        elif verdict == "Request changes" and not blocking and not hidden_blocking:
            bad = "Request changes, but no critical or important finding is blocking."
        if bad:
            if parsed < total and not hidden_blocking:
                bad += " Some cards were not parsed, so this count may be incomplete."
            banners.append(banner("critical", "✖", "Verdict contradicts findings",
                                  e(bad) + " Fix the review file."))
            warn("verdict contradicts findings: " + bad)
        sec_v = norm_verdict(vsec_first) if vsec_first else None
        if sec_v and sec_v != verdict:
            banners.append(banner("important", "▲", "Verdict mismatch",
                                  "The header says %s; the Verdict section says %s." % (e(verdict), e(sec_v))))
    fix = next((ln.strip() for ln in vsec
                if re.sub(r"[*_]", "", ln).strip().startswith("Most important fix first:")), None)
    if fix is None and "Verdict" in by_name:
        warn("Verdict section lacks 'Most important fix first:'")

    fix_text = None
    if fix:
        fix_text = re.sub(r"^[*_]*Most important fix first[*_]*:[*_]*\s*", "", fix)
    if verdict:
        vtone, vglyph, vword = VERDICT_TONE[verdict], VERDICT_GLYPH[verdict], verdict
    else:
        vtone, vglyph, vword = "important", "?", "Verdict unknown"
    verdict_hero = (
        '<section class="verdict tone-%s" aria-labelledby="verdict-h"><p class="eyebrow">Verdict</p>'
        '<h2 class="verdict-word ink tone-%s" id="verdict-h"><span class="glyph" aria-hidden="true">%s</span>'
        '<span>%s</span></h2>%s%s</section>' % (
            vtone, vtone, vglyph, e(vword),
            ('<div class="fix"><p class="label">Most important fix first</p><p class="text">%s</p></div>'
             % inline(fix_text)) if fix else '<div class="fix"><p class="text">No most-important-fix line found.</p></div>',
            ('<p class="strengths">%s</p>' % inline(strengths)) if strengths else ""))

    def meta_item(k):
        v = header[k]
        if k == "Head SHA":
            v = "<code>%s</code>" % e(v[:12])  # the full SHA is in the card footers and the page footer
        elif k == "Since":
            v = "<code>%s</code>" % e(v.strip("`"))
        else:
            v = e(v)
        wide = k == "Title"
        return '<div%s><dt>%s</dt><dd>%s</dd></div>' % (' class="wide"' if wide else "", e(k), v)

    same_title = title is not None and header.get("Title", "").strip() == title.strip()
    meta = "".join(meta_item(k) for k in META_ORDER
                   if k in header and k != "Verdict" and not (k == "Title" and same_title))
    out = ['<main>', '<header class="masthead"><p class="eyebrow">Review dossier</p><h1>%s</h1>'
           '<dl class="meta">%s</dl></header>' % (e(title or "Review"), meta)]
    out += banners
    if structured:
        out.append('<div class="hero">%s%s</div>' % (verdict_hero, render_overview(counts)))
    ordered = sorted(cards, key=lambda c: (SEVERITIES.index(c["severity"]), c["seq"]))
    for heading, axis in SECTIONS[:3]:
        group = [c for c in ordered if c["axis"] == axis]
        gnits = [n for n in nits if n["axis"] == axis]
        if not group and not gnits:
            continue
        out.append('<section class="axis-group"><h2>%s<span class="group-count">%d</span></h2>' % (
            e(heading), len(group) + sum(not n["collapsed"] for n in gnits)))
        out += [render_card(c, sha) for c in group]
        if gnits:
            out.append('<ul class="nits">%s</ul>' % "".join(
                '<li>%s<span>%s</span><span class="unparsed-reason">%s</span></li>'
                % (sevlabel("nit"), ("<code>%s</code> " % e(n["id"]) if n["id"] else "") + inline(n["text"]),
                   e(n["axis"])) for n in gnits))
        out.append("</section>")
    if (not ordered and not nits and structured and total == 0
            and all(h_ in by_name for h_, _ in SECTIONS[:3])):
        out.append("<p>No findings.</p>")
    if unparsed:
        out.append("<h2>Unparsed text</h2>")
        for raw, why in unparsed:
            out.append('<div class="unparsed"><p class="unparsed-reason">Not parsed: %s</p>'
                       '<pre tabindex="0"><code>%s</code></pre></div>' % (e(why), e(raw)))
            warn("unparsed text: %s" % why)

    for c, heading, slines in named:
        if c in known[:3]:
            continue
        if c == "Verdict" and structured:  # the hero shows these lines; keep only what it did not
            used = {strengths, fix}
            if norm_verdict(vsec_first):
                used.add(vsec_first)
            slines = [ln for ln in slines if ln.strip() not in used or not ln.strip()]
            if not "".join(slines).strip():
                continue
        body, unclosed = blocks(slines)
        if unclosed:
            warn("unclosed code fence in section %r" % heading)
        out.append('<section class="quiet"><h2>%s</h2>%s</section>' % (e(heading), body))
    out.append("<footer><p>Generated from %s. This renderer never posts anything.</p>%s</footer>" % (
        e(name), "<p>Head SHA: <code>%s</code></p>" % e(sha) if sha != "unknown" else ""))
    out.append("</main>")

    doc = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n'
           '<meta http-equiv="Content-Security-Policy" content="%s">\n'
           '<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
           '<title>%s</title>\n<style>\n%s</style>\n</head>\n<body>\n%s\n</body>\n</html>\n'
           % (CSP, e("Review: " + title if title else "Review"), CSS, "\n".join(out)))
    return doc, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a bq MR review md to a self-contained html file.")
    ap.add_argument("review", nargs="?", help="path to the review .md")
    ap.add_argument("-o", "--output", help="output path (default: input with .html)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--in-diff", metavar="DIFF", help="print each anchored card's In diff value against "
                    "this `git diff -U0` file; writes and renders nothing")
    ap.add_argument("--repo", help="with --in-diff: the <repo> prefix of anchors")
    mode.add_argument("--previous", metavar="OLD", help="print what the review md dropped or changed against "
                    "OLD, the canonical file it rewrites (R25); writes and renders nothing")
    mode.add_argument("--marker", nargs=3, metavar=("KEY", "SOURCE", "ID"), help="print the posting marker "
                    "sha256(KEY|SOURCE|ID)[:12]; SOURCE is canonical or fresh-<sha7>")
    args = ap.parse_args(argv)
    if args.marker:
        if args.review or args.output or args.repo:
            ap.error("--marker takes no review path, -o or --repo")
        try:
            print(marker(*args.marker))
        except ValueError as ex:
            ap.error(str(ex))
        return 0
    if not args.review:
        ap.error("the review .md path is required")
    src = Path(args.review)
    try:
        text = src.read_bytes().decode("utf-8", errors="replace")
        diff_text = Path(args.in_diff).read_bytes().decode("utf-8", errors="replace") if args.in_diff else None
        old_text = Path(args.previous).read_bytes().decode("utf-8", errors="replace") if args.previous else None
    except OSError as ex:
        print("render_review: cannot read %s (%s)" % (ex.filename or src, type(ex).__name__), file=sys.stderr)
        return 1
    if old_text is not None:
        lines = previous_report(old_text, text)
        for line in lines:
            print(line)
        if any(not ln.startswith(("old file: ", "unrepairable: ")) for ln in lines):
            return 1
        return 3 if any(ln.startswith("unrepairable: ") for ln in lines) else 0  # 2 is argparse's usage error
    if diff_text is not None:
        for line in in_diff_report(text, diff_text, args.repo):
            print(line)
        return 0
    doc, warnings = render(text, src.name)
    for w in warnings:
        print("render_review: warning: " + w, file=sys.stderr)
    out = Path(args.output) if args.output else src.with_suffix(".html")
    if out.resolve() == src.resolve():
        print("render_review: refusing to overwrite the input %s; the output must be a different .html file" % src,
              file=sys.stderr)
        return 1
    if out.exists():
        try:
            head = out.read_bytes()[:15]
        except OSError:
            head = b""
        if head != b"<!DOCTYPE html>":
            print("render_review: refusing to overwrite %s: it does not look like a generated html report" % out,
                  file=sys.stderr)
            return 1
    try:
        out.write_bytes(doc.encode("utf-8"))
    except OSError as ex:
        print("render_review: cannot write %s (%s)" % (out, type(ex).__name__), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
