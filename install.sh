#!/usr/bin/env bash
#
# install.sh — install the "bq" agent team into Claude Code.
#
# Two install paths:
#   1. Native plugin CLI  — uses `claude plugin marketplace add` + `claude plugin install`
#                           (or, when already installed, `claude plugin marketplace update` +
#                           `claude plugin update`). Preferred; used automatically when the
#                           `claude` CLI is on PATH and no manual copy is installed.
#   2. Manual global copy — copies files into ~/.claude/ for environments where the plugin
#                           flow is unavailable (e.g. blocked by policy).
#
# One install at a time: an existing manual copy is kept (never doubled up with the plugin); to
# switch to the plugin run `./install.sh uninstall && ./install.sh plugin`.
#
# Manual-copy namespacing (collision-proof, cleanly removable):
#   commands/<name>.md   -> ~/.claude/commands/bq/<name>.md   (invoked as /bq:<name>)
#   skills/<name>/       -> ~/.claude/skills/bq-<name>/        (skill id bq-<name>)
#   agents/<role>.md     -> ~/.claude/agents/bq/bq-<role>.md   (agent name bq-<role>; plugin
#                           references bq:<role> rewritten to bq-<role> in installed files)
#   templates/           -> ~/.claude/bq-templates/            (home for init/onboard scaffolding)
#
# Usage:
#   ./install.sh install      Auto: refresh an existing manual copy; else install/upgrade the
#                             plugin via the CLI if available; else manual copy
#   ./install.sh plugin       Install/upgrade via the plugin CLI (refuses if a manual copy exists)
#   ./install.sh manual       Force the manual global copy
#   ./install.sh status       Show what is currently installed (plugin + manual)
#   ./install.sh uninstall    Remove the bq install (plugin and/or manual copy)
#   ./install.sh reinstall    uninstall then install again, keeping the current mode
#   ./install.sh clean-legacy Remove only the old flat/mis-nested manual install
#
# Force manual from `install`:   BQ_MANUAL=1 ./install.sh install
# Target dir override:           CLAUDE_CONFIG_DIR=/path ./install.sh manual

set -euo pipefail

# --- paths -------------------------------------------------------------------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# make a dir override absolute (relative = from the current dir) with no ./ segments or trailing
# slash, so recorded manifest paths stay comparable in owned_path (which refuses /./ segments)
abs_dir() {
  local p="$1" dot="/./" sl="/"
  [[ "$p" == /* ]] || p="$PWD/$p"
  while [[ "$p" == */./* ]]; do p="${p//"$dot"/$sl}"; done
  while [[ "$p" == ?*/ ]]; do p="${p%/}"; done
  printf '%s' "$p"
}
CLAUDE_DIR="$(abs_dir "${CLAUDE_CONFIG_DIR:-$HOME/.claude}")"
MANIFEST="$CLAUDE_DIR/.bq-install-manifest"

CMD_DIR="$CLAUDE_DIR/commands/bq"
AGENT_DIR="$CLAUDE_DIR/agents/bq"
SKILL_ROOT="$CLAUDE_DIR/skills"
TEMPLATE_DIR="$CLAUDE_DIR/bq-templates"

# native plugin CLI identifiers (from .claude-plugin/marketplace.json)
MARKETPLACE_NAME="bq"
PLUGIN_ID="bq@bq"

# --- pretty output -----------------------------------------------------------
info()  { printf '  %s\n' "$*"; }
step()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()    { printf '\033[32m✓ %s\033[0m\n' "$*"; }
warn()  { printf '\033[33m! %s\033[0m\n' "$*"; }

# manifest lines: a path to delete (checked by owned_path), or `mkdir:<dir>` — a dir this install
# created, which uninstall only ever rmdir's (so it goes only if empty; never rm -rf'd)
record() { printf '%s\n' "$1" >> "$MANIFEST"; }

# number of arguments — pair with `shopt -s nullglob` to count glob matches (0 when none)
count() { printf '%s' "$#"; }

# is $1 a path this installer owns (and so may delete)? Guards the manifest-driven delete:
# exactly the bq dirs, or a DIRECT child of commands/bq, agents/bq, or a skills/bq-* entry — never
# CLAUDE_DIR or the shared skills/ root, never anything deeper (which could sit behind a symlink),
# never a `..` or `.` segment. Callers strip trailing slashes and unlink symlinks, never recurse.
# a recorded mkdir: entry is only trusted if it is one of our target dirs or an ancestor of one
# (exactly what `mkdir -p` creates) — a tampered manifest can't point rmdir anywhere else
created_dir() {
  local d="$1" root
  for root in "$CMD_DIR" "$AGENT_DIR" "$SKILL_ROOT" "$TEMPLATE_DIR"; do
    [[ "$root" == "$d" || "$root" == "$d"/* ]] && return 0
  done
  return 1
}

owned_path() {
  local p="$1" rest
  [[ -n "$p" && "$p" != "/" ]] || return 1
  case "/$p/" in */../*|*/./*) return 1 ;; esac
  case "$p" in "$CMD_DIR"|"$AGENT_DIR"|"$TEMPLATE_DIR") return 0 ;; esac
  case "$p" in
    # a symlinked parent would make rm -rf act outside bq's tree
    "$CMD_DIR"/?*)       [[ -L "$CMD_DIR" ]] && return 1; rest="${p#"$CMD_DIR"/}" ;;
    "$AGENT_DIR"/?*)     [[ -L "$AGENT_DIR" ]] && return 1; rest="${p#"$AGENT_DIR"/}" ;;
    "$SKILL_ROOT"/bq-*)  rest="${p#"$SKILL_ROOT"/}" ;;
    *) return 1 ;;
  esac
  [[ "$rest" != */* ]]
}

# delete an owned path: a symlink is unlinked (never followed), anything else removed recursively
remove_path() {
  if [[ -L "$1" ]]; then rm -f "$1"; elif [[ -e "$1" ]]; then rm -rf "$1"; else return 1; fi
  info "removed $1"
}

require_claude_dir() {
  if [[ ! -d "$CLAUDE_DIR" ]]; then
    warn "Claude config dir not found: $CLAUDE_DIR"
    info "Create it and re-run, or set CLAUDE_CONFIG_DIR to your Claude dir."
    exit 1
  fi
}

# --- legacy cleanup ----------------------------------------------------------
# Removes the older flat / mis-nested copy. The delete list is derived from the
# repo's own filenames, so it only ever touches files this plugin owns.
clean_legacy() {
  step "Cleaning up legacy install"
  local removed=0

  # flat commands: ~/.claude/commands/<name>.md
  for f in "$REPO_DIR"/commands/*.md; do
    [[ -e "$f" ]] || continue
    local legacy
    legacy="$CLAUDE_DIR/commands/$(basename "$f")"
    if [[ -f "$legacy" ]]; then rm -f "$legacy"; info "removed $legacy"; removed=1; fi
  done

  # flat agents: ~/.claude/agents/bq-<role>.md
  for f in "$REPO_DIR"/agents/*.md; do
    [[ -e "$f" ]] || continue
    local legacy
    legacy="$CLAUDE_DIR/agents/bq-$(basename "$f")"
    if [[ -f "$legacy" ]]; then rm -f "$legacy"; info "removed $legacy"; removed=1; fi
  done

  # mis-nested skills: ~/.claude/skills/bq/<skill>/
  if [[ -d "$SKILL_ROOT/bq" ]]; then
    rm -rf "$SKILL_ROOT/bq"; info "removed $SKILL_ROOT/bq"; removed=1
  fi

  if [[ "$removed" -eq 1 ]]; then ok "Legacy install removed"; else info "No legacy install found"; fi
}

# --- skill name prefixing ----------------------------------------------------
# bq-team -> bq-team ; memory -> bq-memory
bq_name() {
  case "$1" in
    bq-*) printf 'bq-%s' "${1#bq-}" ;;  # normalize, no double prefix
    *)      printf 'bq-%s' "$1" ;;
  esac
}

# manual installs name agents bq-<role> (plugin installs scope them as bq:<role>). Rewrite the
# frontmatter name (bounded to the frontmatter: stops at the closing ---), resolve the claude-only
# spans, and rewrite agent references bq:<role> -> bq-<role>. The (?<![/\w]) guard leaves
# /bq:<command> slash commands alone; only the seven role names are touched.
# claude-only spans: `<!-- claude-only -->A<!-- copilot: B --><!-- /claude-only -->` is still Claude,
# so keep A (the copilot alternative is for install-copilot.sh); the newline after the closer is
# eaten only when the opener's was (a block span), so an inline span doesn't glue words. A plain
# `<!-- claude-only -->A<!-- /claude-only -->` is the plugin-vs-manual naming clause -> manual form.
localize_agent_names() {
  local file="$1" newname="${2:-}" tmp
  tmp="$(mktemp)"
  NN="$newname" perl -0777 -pe '
    s/\A(---\n(?:(?!---\n)[^\n]*\n)*?)name:[^\n]*/$1name: $ENV{NN}/ if length $ENV{NN};
    s{<!--\s*claude-only\s*-->(\n)?((?:(?!<!--\s*/?claude-only).)*?)<!--\s*copilot:(?:(?!-->).)*-->\s*?<!--\s*/claude-only\s*-->(?(1)\n?)}{$2}gs;
    s{<!--\s*claude-only\s*-->(?:(?!<!--\s*/?claude-only|<!--\s*copilot:).)*?<!--\s*/claude-only\s*-->}{`bq-<role>` (e.g. `bq-engineer`)}gs;
    s/(?<![\/\w])bq:(maestro|architect|engineer|tester|reviewer|researcher|scribe)\b/bq-$1/g;
  ' "$file" > "$tmp"
  mv "$tmp" "$file"
}

# point the installed bq-memory template lookup at this install's real paths (CLAUDE_CONFIG_DIR aware)
localize_memory_paths() {
  local file="$1" tmp
  [[ -f "$file" ]] || return 0
  tmp="$(mktemp)"
  TD="$TEMPLATE_DIR" CD="$CLAUDE_DIR" perl -pe 's{~/\.claude/bq-templates/bq/}{$ENV{TD}/bq/}g; s{~/\.claude/plugins/cache/}{$ENV{CD}/plugins/cache/}g' "$file" > "$tmp"
  mv "$tmp" "$file"
}

# --- native plugin CLI path --------------------------------------------------
have_claude_cli() { command -v claude >/dev/null 2>&1; }

# is the bq plugin currently installed via the claude CLI?
# (exact `bq@bq` token; output captured first so grep -q can't SIGPIPE the CLI under pipefail)
plugin_installed() {
  have_claude_cli || return 1
  local out
  out="$(claude plugin list 2>/dev/null)" || return 1
  grep -qE '(^|[[:space:]])bq@bq([[:space:]]|$)' <<< "$out"
}

have_manual_install() { [[ -f "$MANIFEST" ]]; }

# attempt the plugin CLI install; returns non-zero on failure without exiting
# (call in an `if` so set -e is suspended and the caller can fall back)
_plugin_install_attempt() {
  have_claude_cli || return 1
  info "marketplace add: $REPO_DIR"
  claude plugin marketplace add "$REPO_DIR" \
    || warn "marketplace add reported an issue (already added or blocked); continuing"
  # an already-added marketplace keeps its old snapshot; refresh it so the install gets current files
  claude plugin marketplace update "$MARKETPLACE_NAME" \
    || warn "marketplace update reported an issue; continuing"
  info "plugin install: $PLUGIN_ID"
  claude plugin install "$PLUGIN_ID" -y
}

# upgrade an installed plugin in place; never falls back to a manual copy (that would double-install)
do_plugin_upgrade() {
  step "Upgrading bq via the Claude Code plugin CLI"
  info "marketplace update: $MARKETPLACE_NAME (pulls from wherever that marketplace was added from)"
  if ! claude plugin marketplace update "$MARKETPLACE_NAME"; then
    warn "Marketplace update failed — $PLUGIN_ID left as it was."
    exit 1
  fi
  info "plugin update: $PLUGIN_ID"
  if ! claude plugin update "$PLUGIN_ID" -y; then
    warn "Plugin update failed — $PLUGIN_ID left as it was."
    exit 1
  fi
  ok "Updated $PLUGIN_ID via the plugin CLI"
  info "Restart Claude Code to apply the update."
}

# refuse the plugin path while a manual copy is installed (both would load: a double install)
refuse_if_manual() {
  if have_manual_install; then
    warn "A manual bq copy is installed ($MANIFEST) — not adding the plugin on top of it."
    info "Switch to the plugin with: $0 uninstall && $0 plugin"
    exit 1
  fi
}

do_plugin_install() {
  if ! have_claude_cli; then
    warn "claude CLI not found on PATH — cannot use the plugin flow."
    info "Install the Claude Code CLI, or run: $0 manual"
    exit 1
  fi
  refuse_if_manual
  if plugin_installed; then do_plugin_upgrade; return; fi
  step "Installing bq via the Claude Code plugin CLI"
  if _plugin_install_attempt; then
    ok "Installed $PLUGIN_ID via the plugin CLI"
    info "Restart Claude Code (or reload with /plugin) to pick it up."
  else
    warn "Plugin install failed — often an enterprise policy blocking local marketplaces."
    info "Use the manual file-copy install instead: $0 manual"
    exit 1
  fi
}

# returns non-zero if the plugin is installed but the CLI failed to remove it
do_plugin_uninstall() {
  have_claude_cli || return 0
  plugin_installed || return 0
  step "Uninstalling bq via the Claude Code plugin CLI"
  if claude plugin uninstall "$PLUGIN_ID" -y; then
    ok "Removed $PLUGIN_ID (marketplace '$MARKETPLACE_NAME' left in place)"
  else
    warn "Plugin uninstall failed — $PLUGIN_ID is still installed."
    return 1
  fi
}

# --- install (auto: plugin CLI if available, else manual copy) ---------------
do_install() {
  if [[ "${BQ_MANUAL:-0}" == "1" ]]; then
    info "BQ_MANUAL=1 — using the manual file-copy install."
    do_manual_install
  elif have_manual_install; then
    info "Existing manual install found ($MANIFEST) — refreshing it, not adding the plugin on top."
    do_manual_install
    info "To switch to the plugin instead: $0 uninstall && $0 plugin"
  elif have_claude_cli && plugin_installed; then
    do_plugin_upgrade
  elif have_claude_cli; then
    step "Installing bq via the Claude Code plugin CLI"
    info "(force the file-copy install with: $0 manual)"
    if _plugin_install_attempt; then
      ok "Installed $PLUGIN_ID via the plugin CLI"
      info "Restart Claude Code (or reload with /plugin) to pick it up."
    else
      warn "Plugin CLI install failed (e.g. policy blocks local marketplaces) — falling back to the manual copy."
      do_manual_install
    fi
  else
    info "claude CLI not found — using the manual file-copy install."
    do_manual_install
  fi
}

# --- manual global copy ------------------------------------------------------
do_manual_install() {
  require_claude_dir
  # a manual copy on top of the plugin doubles every agent, skill and command
  if plugin_installed; then
    warn "bq is already installed as a plugin ($PLUGIN_ID) — a manual copy would duplicate it."
    info "Remove the plugin first: claude plugin uninstall $PLUGIN_ID -y   (then re-run: $0 manual)"
    exit 1
  fi
  clean_legacy

  step "Installing bq into $CLAUDE_DIR"
  # note the dirs this install creates (deepest first) so uninstall can rmdir them if left empty
  # (carrying over any recorded by a previous install, so re-running install doesn't forget them)
  local created=() d
  if [[ -f "$MANIFEST" ]]; then
    while IFS= read -r d; do
      [[ "$d" == mkdir:* ]] && created+=("${d#mkdir:}")
    done < "$MANIFEST"
  fi
  for d in "$CMD_DIR" "$AGENT_DIR" "$SKILL_ROOT"; do
    while [[ ! -e "$d" ]]; do created+=("$d"); d="$(dirname "$d")"; done
  done
  mkdir -p "$CMD_DIR" "$AGENT_DIR" "$SKILL_ROOT"
  : > "$MANIFEST"   # fresh manifest
  for d in ${created[@]+"${created[@]}"}; do record "mkdir:$d"; done

  # commands -> commands/bq/
  record "$CMD_DIR"
  local n_cmd=0
  for f in "$REPO_DIR"/commands/*.md; do
    [[ -e "$f" ]] || continue
    local dest
    dest="$CMD_DIR/$(basename "$f")"
    cp "$f" "$dest"; localize_agent_names "$dest"; record "$dest"; n_cmd=$((n_cmd+1))
  done
  ok "$n_cmd commands -> $CMD_DIR  (/bq:<name>)"

  # agents -> agents/bq/bq-<role>.md  (name: bq-<role>)
  record "$AGENT_DIR"
  local n_agent=0
  for f in "$REPO_DIR"/agents/*.md; do
    [[ -e "$f" ]] || continue
    local role dest
    role="$(basename "$f" .md)"
    dest="$AGENT_DIR/bq-$role.md"
    cp "$f" "$dest"; localize_agent_names "$dest" "bq-$role"; record "$dest"; n_agent=$((n_agent+1))
  done
  ok "$n_agent agents -> $AGENT_DIR"

  # skills -> skills/bq-<name>/  (rewrite name: field)
  local n_skill=0
  for d in "$REPO_DIR"/skills/*/; do
    [[ -d "$d" ]] || continue
    local base newname dest
    base="$(basename "$d")"
    newname="$(bq_name "$base")"
    dest="$SKILL_ROOT/$newname"
    rm -rf "$dest"
    cp -R "$d" "$dest"
    local md
    while IFS= read -r md; do
      if [[ "$md" == "$dest/SKILL.md" ]]; then
        localize_agent_names "$md" "$newname"
      else
        localize_agent_names "$md"
      fi
    done < <(find "$dest" -type f -name '*.md')
    record "$dest"; n_skill=$((n_skill+1))
  done
  ok "$n_skill skills -> $SKILL_ROOT/bq-*"

  # templates -> bq-templates/
  if [[ -d "$REPO_DIR/templates" ]]; then
    rm -rf "$TEMPLATE_DIR"
    cp -R "$REPO_DIR/templates" "$TEMPLATE_DIR"
    record "$TEMPLATE_DIR"
    localize_memory_paths "$SKILL_ROOT/bq-memory/SKILL.md"
    ok "templates -> $TEMPLATE_DIR  (bq-memory lookup pointed at $TEMPLATE_DIR/bq/)"
  fi

  step "Done"
  ok "Installed $n_agent agents, $n_cmd commands, $n_skill skills"
  info "Commands are namespaced: /bq:build, /bq:status, /bq:brainstorm …"
  info "Restart Claude Code (or reload) to pick them up."
}

# --- uninstall ---------------------------------------------------------------
do_uninstall() {
  # native plugin install first (no-op if not present); a failure is reported at the end
  local plugin_failed=0
  do_plugin_uninstall || plugin_failed=1

  step "Uninstalling bq from $CLAUDE_DIR"
  local removed=0

  # dirs the install created (mkdir: lines; manifests from older installs have none, so their
  # parent dirs are simply left in place)
  local made=() p
  if [[ -f "$MANIFEST" ]]; then
    while IFS= read -r p; do
      [[ "$p" == mkdir:* ]] && made+=("${p#mkdir:}")
    done < "$MANIFEST"
    # remove in reverse so files go before their dirs
    while IFS= read -r p; do
      [[ -n "$p" && "$p" != mkdir:* ]] || continue
      while [[ "$p" == */ ]]; do p="${p%/}"; done
      if ! owned_path "$p"; then warn "refusing manifest entry outside bq's install paths: $p"; continue; fi
      if remove_path "$p"; then removed=1; fi
    done < <(tac "$MANIFEST" 2>/dev/null || tail -r "$MANIFEST")
    rm -f "$MANIFEST"
  else
    warn "No manifest found; falling back to known locations"
  fi

  # fallback / belt-and-suspenders for the known layout — only names this repo ships, so a
  # user's own bq-* skill is never swept up
  local d s
  local known=("$CMD_DIR" "$AGENT_DIR" "$TEMPLATE_DIR")
  for s in "$REPO_DIR"/skills/*/; do
    [[ -d "$s" ]] && known+=("$SKILL_ROOT/$(bq_name "$(basename "$s")")")
  done
  for d in "${known[@]}"; do
    [[ -L "$d" || -d "$d" ]] || continue
    if remove_path "$d"; then removed=1; fi
  done

  # tidy only the dirs this install recorded as created — rmdir only succeeds on empty dirs, so
  # one now holding the user's own files stays; two passes so a parent listed before its child goes
  for d in ${made[@]+"${made[@]}"} ${made[@]+"${made[@]}"}; do
    created_dir "$d" || continue
    rmdir "$d" 2>/dev/null || true
  done

  if [[ "$plugin_failed" -eq 1 ]]; then
    warn "Uninstall incomplete: the plugin CLI could not remove $PLUGIN_ID (retry: claude plugin uninstall $PLUGIN_ID)"
    return 1
  fi
  if [[ "$removed" -eq 1 ]]; then ok "bq uninstalled"; else info "Nothing to uninstall"; fi
}

# uninstall then install again in the same mode (decided before uninstall deletes the manifest)
do_reinstall() {
  if have_manual_install; then
    do_uninstall; do_manual_install
  elif plugin_installed; then
    do_uninstall; do_plugin_install
  else
    do_uninstall; do_install
  fi
}

# --- status ------------------------------------------------------------------
do_status() {
  step "bq install status"

  # native plugin
  if have_claude_cli; then
    if plugin_installed; then
      ok "Plugin: installed via the claude CLI"
      claude plugin list 2>/dev/null | grep -E '(^|[[:space:]])bq@bq([[:space:]]|$)' | sed 's/^/    /' || true
    else
      info "Plugin: not installed via the claude CLI"
    fi
  else
    info "Plugin: claude CLI not found on PATH"
  fi

  # manual copy
  if [[ -f "$MANIFEST" ]]; then
    local n_cmd n_agent n_skill
    shopt -s nullglob
    n_cmd=$(count "$CMD_DIR"/*.md)
    n_agent=$(count "$AGENT_DIR"/*.md)
    n_skill=$(count "$SKILL_ROOT"/bq-*/)
    shopt -u nullglob
    ok "Manual: installed in $CLAUDE_DIR"
    info "commands:  $n_cmd  ($CMD_DIR)"
    info "agents:    $n_agent  ($AGENT_DIR)"
    info "skills:    $n_skill  ($SKILL_ROOT/bq-*)"
    if [[ -d "$TEMPLATE_DIR" ]]; then info "templates: $TEMPLATE_DIR"; fi
    info "manifest:  $MANIFEST"
  else
    info "Manual: not installed (no manifest at $MANIFEST)"
  fi
}

# --- usage -------------------------------------------------------------------
# prints the leading comment block (line 2 up to the first non-comment line)
usage() {
  awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "${BASH_SOURCE[0]}"
}

# --- main --------------------------------------------------------------------
case "${1:-install}" in
  install)      do_install ;;
  plugin)       do_plugin_install ;;
  manual)       do_manual_install ;;
  status)       do_status ;;
  uninstall)    do_uninstall ;;
  reinstall)    do_reinstall ;;
  clean-legacy) require_claude_dir; clean_legacy ;;
  -h|--help|help)
    usage
    ;;
  *)
    warn "Unknown command: $1"
    info "Use: install | plugin | manual | status | uninstall | reinstall | clean-legacy"
    exit 1
    ;;
esac
