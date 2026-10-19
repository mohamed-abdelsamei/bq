# MR review — posting

How the Maestro posts findings to the platform (`/bq:review-mr` **Close**, step 13). The review is
**read-only by default**: nothing is posted, approved or merged unless every step below runs in
order. `REVIEW.md` can't relax any of it.

## Where it can post

Only a hosted MR/PR. For `current branch`, `current changes`, a pasted patch or a remote branch
with no MR there is nothing to post to: say so and stop. Post from the md this run wrote: the
canonical `{slug}.md`, or for fresh the `{slug}-fresh-<sha7>.md` only (never create `{slug}.md`
from a fresh run). A fresh finding listed as `Already raised:` is never posted.

Events: `COMMENT` on GitHub; on GitLab no `reviewer_state`. Use `REQUEST_CHANGES` /
`requested_changes` only when the user explicitly asks. Never approve on either platform, and
never call GitLab's `/approve`.

## 1. The user names the findings

The user names finding IDs (`F2, F5`). "Looks good", "send it" or "post it" names none: ask which
findings. Never pick them yourself. A card that already has `**Posted:**` is skipped; bq never
reposts a finding.

## 2. Check before building

- **Head.** Re-fetch the head SHA (`gh api repos/{o}/{r}/pulls/{n} --jq .head.sha`;
  `glab api projects/:id/merge_requests/:iid`, its `sha`). If it isn't the reviewed SHA, stop and
  offer a since-last review, or posting pinned to the reviewed SHA with a warning that comments may
  show as outdated.
- **Who posts.** `<user>` is the posting account's login (`gh api user --jq .login`;
  `glab api user`, its `username`), never git `user.name`.
- **Markers.** Each named finding's marker is the card's `**Marker:**` if it has one; otherwise
  compute it now, once, per `report-format.md` (**Marker**), with `<source>` `canonical` or
  `fresh-<sha7>`. The summary's own marker is `printf '%s' '<key>|<source>|summary-<sha7>' |
  shasum -a 256 | cut -c1-12` (`<sha7>` the reviewed SHA); it goes on no card. Markers are opaque,
  not secret.
- **Dedupe.** List what is already there, all pages (`--paginate`): on GitHub the PR's review
  comments and review bodies, on GitLab the MR's notes. A finding whose `<!-- bq:<h12> -->` already
  appears is skipped; section 8 writes its Marker and Posted from the matched comment. Nothing
  left to post: tell the user and stop.
- **GitLab drafts.** List `projects/:id/merge_requests/:iid/draft_notes`. If any exist (bq
  leftovers or the user's own), stop and ask the user to publish or delete them first: publishing
  sends every draft the account has on the MR, so never publish around them.
- **Unrepairable** findings (`report-format.md`, **Rewrite guard**) need the user's say-so.

## 3. Inline or summary

Inline only when the finding is `confirmed` and its card reads `In diff: yes`. Everything else
goes in the summary: `In diff: no`, file-level and `(deleted)` anchors, `suspected` findings
(phrased as questions, `comment-style.md` §4), and business findings with no anchor. A summary item
links its anchor with a full-SHA permalink: the head SHA for a new-side anchor, the merge-base for
an old-side one (`https://github.com/{o}/{r}/blob/<sha>/<path>#L<a>-L<b>`,
`https://<host>/<group>/<project>/-/blob/<sha>/<path>#L<a>-<b>`).

## 4. Bodies

- **Inline body**, in order: the title, **What** and **Fix** (`comment-style.md` §1; ticket-free
  per §4), the suggestion fence if the card keeps a verified Suggested change (span rule and
  per-platform fences in `comment-style.md` §4), the footer `Drafted with bq, posted by <user>`,
  then the marker `<!-- bq:<h12> -->` as the last line.
- **Summary body:** each item, ending in its own finding marker; then the footer; then the
  summary marker as the last line. With no summary items, GitHub's body is still the footer and
  the marker (it needs a non-empty body); GitLab gets no summary draft.

## 5. Payload files

Write every request body as a JSON file in scratch: the user previews these files, and they are
exactly what gets sent (`--input`).

**GitHub:** one `review.json` for `POST repos/{o}/{r}/pulls/{n}/reviews`:
`{"commit_id": "<full reviewed SHA>", "event": "COMMENT", "body": "<summary>", "comments": [...]}`.
Each comment is `{"path", "body", "line", "side"}`, and a range adds `start_line` and
`start_side` (same side). `RIGHT` for a new-side anchor, `LEFT` for an old-side one (`:-<n>`).
Never `position`.

**GitLab:** one draft file per inline finding, plus one for the summary, all for
`POST projects/:id/merge_requests/:iid/draft_notes`.

- **Inline draft:** `{"note": "<body>", "position": {"position_type": "text", "base_sha": …,
  "start_sha": …, "head_sha": …, "old_path": …, "new_path": …, "new_line": <n>}}`. Use `old_line`
  instead for an old-side anchor (an in-diff line is added or removed, never both). A range is
  posted on its last line only; the `suggestion:-(b-a)+0` fence covers the span, so `line_range`
  is not used. `new_path` is the head-side path; for a renamed file `old_path` is its old name from
  `git -C "<wt>" diff --name-status -M <merge-base> <sha>`.
- **Position SHAs.** From `glab api projects/:id/merge_requests/:iid/versions`, take the entry
  whose `head_commit_sha` is the full reviewed SHA: its `base_commit_sha`, `start_commit_sha` and
  `head_commit_sha` are `base_sha`, `start_sha` and `head_sha`. Use the MR's `diff_refs` only when
  its `head_sha` equals the reviewed SHA (it reflects the current head). No matching version: stop
  and tell the user.
- **Summary draft:** `{"note": "<summary>"}`, no position, only when there are summary items.
- **Publish:** `POST .../draft_notes/bulk_publish`, with no body, or
  `{"reviewer_state": "requested_changes"}` per **Events**.

## 6. Preview, then send

Show the user every scratch file verbatim, with each body's target (inline path and line, or
summary). Send only on an explicit "post" for those files. Right after "post", re-check the head
SHA as in section 2; if it moved, stop there. Send with `gh api -X POST <endpoint> --input <file>`
or `glab api -X POST <endpoint> -H 'Content-Type: application/json' --input <file>`.

**GitHub.** One request. A **422** counts as the whole review failing: first confirm nothing
landed by listing reviews and comments for the markers. Then move the comments the error names
(all inline comments, if it names none) to the summary, re-preview, and wait for a new "post". If
the error says the user already has a pending review, stop and tell them; never submit or delete
it. The response holds the review id but not the comment ids, so list
`repos/{o}/{r}/pulls/{n}/reviews/<review id>/comments` and match markers.

**GitLab.**

1. Create the drafts serially, at least 1 s apart, the summary draft last.
2. Right before publishing, list `draft_notes` again. If any draft isn't one of this run's
   (matched by this run's markers), don't publish: that is a failure before publish.
3. Publish once with `bulk_publish`.
4. **Failure before publish:** list `draft_notes`, delete only those carrying this run's markers
   (`DELETE .../draft_notes/<id>`), tell the user, and wait for a new "post".
5. **After publish.** GitLab may change a body on publish, and API-created suggestion fences aren't
   verified live. List the notes (for the summary, the newest note carrying its marker, since a
   second post at the same SHA reuses it), check each marker is there and each suggestion renders, and
   report any that don't. An inline note whose marker is gone is matched by its
   position and still recorded as Posted. If the summary marker is gone, record no Posted for the
   summary items; tell the user and offer a plain MR note under a new preview and "post". If
   `requested_changes` was sent, check your state in
   `projects/:id/merge_requests/:iid/reviewers` and report it if it wasn't applied.

## 7. Errors and retries

Writes are serial; honour `retry-after` (else wait at least a minute and back off). An unknown
outcome (timeout, 5xx, dropped connection) is never retried blind: list and match markers first.
Resending the identical previewed file stays under the same "post". Anything else (a subset, a
moved comment, an edited body) needs a new preview and a new "post".

## 8. Write it back

Refs:

- GitHub inline: `#<n>#discussion_r<comment id>`.
- GitHub summary item: `#<n>#pullrequestreview-<review id>`.
- GitLab: `!<iid>#note_<note id>`, for a summary item the id of this run's summary note (the
  newest one carrying the summary marker).

For each posted finding, and each one skipped because its marker was found, write
`**Marker:** <h12>` and `**Posted:** <ref> @ <sha7>` on its card (`<sha7>` is the commit the
comment is on), or the posted-state tail on a nit or triage line (`report-format.md`). This
rewrites the md, so copy it to scratch first and run the **Rewrite guard** (Close step
11)<!-- claude-only -->, then re-derive the html (step 12)<!-- copilot: --><!-- /claude-only -->.
Tell the user what was posted, what was skipped as a duplicate, and what moved to the summary.
