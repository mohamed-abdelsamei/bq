#!/usr/bin/env python3
"""Render a /bq:review-mr report (markdown) to one self-contained HTML file. Stdlib only.

Usage: python3 scripts/render_review.py <review.md> [-o out.html]

The md is the source of truth (format: skills/mr-review/references/report-format.md); the html is
derived and regenerable. Same input gives byte-identical output (no timestamps). Parsing is strict:
a `###` card that does not parse is shown escaped under a visible "N of M cards parsed" banner, never
dropped, and counts come only from parsed cards. Odd input shows visible banners in the html and warnings on stderr (exit 0);
the exit code is non-zero only when the input file cannot be read (or the output cannot be written).

Every md-derived string is escaped with html.escape(quote=True). There is no raw HTML and no links.
"""
import argparse
import html
import re
import sys
from pathlib import Path

SEVERITIES = ("critical", "important", "minor", "nit")
BLOCKING = ("critical", "important")
AXES = ("code", "business", "process")
CONFIDENCE = ("confirmed", "suspected")
VERDICTS = ("Approve", "Approve with changes", "Request changes")
HEADER_KEYS = ("MR", "Title", "Head SHA", "Target", "Date", "Reviewers", "Verdict")
META_ORDER = ("MR", "Head SHA", "Target", "Date", "Reviewers", "Title")  # Title last: it can be long
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
NIT_START = re.compile(r"^- \[nit\]", re.I)
SEV_HEAD = re.compile(r"^### \[(critical|important)\]", re.I)
LIST_ITEM = re.compile(r"^\s*(?:([-*+])|\d+[.)])\s+(.*)$")
BOLD = re.compile(r"\*\*(.+?)\*\*")


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
            if m and m.group(1).strip() in HEADER_KEYS:
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
            nits.append({"text": NIT.match(line).group(1), "axis": section_axis})
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
        if k in ("Axis", "Confidence", "Anchor"):
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
        '<article class="finding tone-%s"><header class="f-head"><h3>%s</h3><p class="f-meta">%s%s<span class="tag %s">%s</span>%s</p></header>'
        '<dl class="rows">%s</dl>'
        '<p class="f-foot">Axis: %s &middot; Head SHA: <code>%s</code></p></article>'
        % (sev, inline(card["title"]), sevlabel(sev),
           '<span class="tag blocking">Blocking</span>' if sev in BLOCKING else '<span class="tag">Non-blocking</span>',
           conf, ("&#10003; " if conf == "confirmed" else "? ") + conf.capitalize(),
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

    cards, nits = [], []
    for heading, axis in SECTIONS[:3]:
        if heading not in by_name:
            continue
        c, n, u = parse_findings(by_name[heading], axis, warn)
        cards += [dict(x, seq=len(cards) + i) for i, x in enumerate(c)]
        nits += n
        unparsed += u
    parsed = len(cards)

    counts = {(s, a): 0 for s in SEVERITIES for a in AXES}
    for c in cards:
        counts[(c["severity"], c["axis"])] += 1
    for n in nits:
        counts[("nit", n["axis"])] += 1
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
            e(heading), len(group) + len(gnits)))
        out += [render_card(c, sha) for c in group]
        if gnits:
            out.append('<ul class="nits">%s</ul>' % "".join(
                '<li>%s<span>%s</span><span class="unparsed-reason">%s</span></li>'
                % (sevlabel("nit"), inline(n["text"]), e(n["axis"])) for n in gnits))
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
    ap.add_argument("review", help="path to the review .md")
    ap.add_argument("-o", "--output", help="output path (default: input with .html)")
    args = ap.parse_args(argv)
    src = Path(args.review)
    try:
        text = src.read_bytes().decode("utf-8", errors="replace")
    except OSError as ex:
        print("render_review: cannot read %s (%s)" % (src, type(ex).__name__), file=sys.stderr)
        return 1
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
