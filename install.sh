#!/usr/bin/env bash
#
# install.sh — install the "bq" agent team into Claude Code.
#
# Two install paths:
#   1. Native plugin CLI  — uses `claude plugin marketplace add` + `claude plugin install`.
#                           Preferred; used automatically when the `claude` CLI is on PATH.
#   2. Manual global copy — copies files into ~/.claude/ for environments where the plugin
#                           flow is unavailable (e.g. blocked by policy).
#
# Manual-copy namespacing (collision-proof, cleanly removable):
#   commands/<name>.md   -> ~/.claude/commands/bq/<name>.md   (invoked as /bq:<name>)
#   skills/<name>/       -> ~/.claude/skills/bq-<name>/        (skill id bq-<name>)
#   agents/<role>.md     -> ~/.claude/agents/bq/bq-<role>.md   (agent name bq-<role>; plugin
#                           references bq:<role> rewritten to bq-<role> in installed files)
#   templates/           -> ~/.claude/bq-templates/            (home for init/onboard scaffolding)
#
# Usage:
#   ./install.sh install      Auto: plugin CLI if available, else manual copy
#   ./install.sh plugin       Force the native plugin CLI install
#   ./install.sh manual       Force the manual global copy
#   ./install.sh status       Show what is currently installed (plugin + manual)
#   ./install.sh uninstall    Remove the bq install (plugin and/or manual copy)
#   ./install.sh reinstall    uninstall then install
#   ./install.sh clean-legacy Remove only the old flat/mis-nested manual install
#
# Force manual from `install`:   BQ_MANUAL=1 ./install.sh install
# Target dir override:           CLAUDE_CONFIG_DIR=/path ./install.sh manual

set -euo pipefail

# --- paths -------------------------------------------------------------------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
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

record() { printf '%s\n' "$1" >> "$MANIFEST"; }

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
    local legacy="$CLAUDE_DIR/commands/$(basename "$f")"
    if [[ -f "$legacy" ]]; then rm -f "$legacy"; info "removed $legacy"; removed=1; fi
  done

  # flat agents: ~/.claude/agents/bq-<role>.md
  for f in "$REPO_DIR"/agents/*.md; do
    [[ -e "$f" ]] || continue
    local legacy="$CLAUDE_DIR/agents/bq-$(basename "$f")"
    if [[ -f "$legacy" ]]; then rm -f "$legacy"; info "removed $legacy"; removed=1; fi
  done

  # mis-nested skills: ~/.claude/skills/bq/<skill>/
  if [[ -d "$SKILL_ROOT/bq" ]]; then
    rm -rf "$SKILL_ROOT/bq"; info "removed $SKILL_ROOT/bq"; removed=1
  fi

  [[ "$removed" -eq 1 ]] && ok "Legacy install removed" || info "No legacy install found"
}

# --- skill name prefixing ----------------------------------------------------
# bq-team -> bq-team ; memory -> bq-memory
bq_name() {
  case "$1" in
    bq-*) printf 'bq-%s' "${1#bq-}" ;;  # normalize, no double prefix
    *)      printf 'bq-%s' "$1" ;;
  esac
}

# rewrite the frontmatter `name:` line in a SKILL.md to $2
set_skill_name() {
  local file="$1" newname="$2" tmp
  tmp="$(mktemp)"
  awk -v n="$newname" '
    BEGIN { done=0 }
    /^name:[[:space:]]/ && !done { print "name: " n; done=1; next }
    { print }
  ' "$file" > "$tmp"
  mv "$tmp" "$file"
}

# manual installs name agents bq-<role> (plugin installs scope them as bq:<role>). Rewrite the
# frontmatter name, collapse the claude-only "plugin vs manual" naming clause to the manual form,
# and rewrite agent references bq:<role> -> bq-<role>. The (?<![/\w]) guard leaves /bq:<command>
# slash commands alone; only the seven role names are touched.
localize_agent_names() {
  local file="$1" newname="${2:-}" tmp
  tmp="$(mktemp)"
  NN="$newname" perl -0777 -pe '
    s/\A(---\n(?:.*\n)*?)name:[^\n]*/$1name: $ENV{NN}/ if length $ENV{NN};
    s{<!--\s*claude-only\s*-->.*?<!--\s*/claude-only\s*-->}{`bq-<role>` (e.g. `bq-engineer`)}gs;
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
plugin_installed() {
  have_claude_cli || return 1
  claude plugin list 2>/dev/null | grep -qiE '(^|[^[:alnum:]])bq([^[:alnum:]]|$)'
}

# attempt the plugin CLI install; returns non-zero on failure without exiting
# (call in an `if` so set -e is suspended and the caller can fall back)
_plugin_install_attempt() {
  have_claude_cli || return 1
  info "marketplace add: $REPO_DIR"
  claude plugin marketplace add "$REPO_DIR" \
    || warn "marketplace add reported an issue (already added or blocked); continuing"
  info "plugin install: $PLUGIN_ID"
  claude plugin install "$PLUGIN_ID" -y
}

do_plugin_install() {
  if ! have_claude_cli; then
    warn "claude CLI not found on PATH — cannot use the plugin flow."
    info "Install the Claude Code CLI, or run: $0 manual"
    exit 1
  fi
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

do_plugin_uninstall() {
  have_claude_cli || return 0
  plugin_installed || return 0
  step "Uninstalling bq via the Claude Code plugin CLI"
  claude plugin uninstall "$PLUGIN_ID" -y \
    || warn "plugin uninstall reported an issue"
  ok "Removed $PLUGIN_ID (marketplace '$MARKETPLACE_NAME' left in place)"
}

# --- install (auto: plugin CLI if available, else manual copy) ---------------
do_install() {
  if [[ "${BQ_MANUAL:-0}" == "1" ]]; then
    info "BQ_MANUAL=1 — using the manual file-copy install."
    do_manual_install
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
  clean_legacy

  step "Installing bq into $CLAUDE_DIR"
  : > "$MANIFEST"   # fresh manifest

  # commands -> commands/bq/
  mkdir -p "$CMD_DIR"; record "$CMD_DIR"
  local n_cmd=0
  for f in "$REPO_DIR"/commands/*.md; do
    [[ -e "$f" ]] || continue
    local dest="$CMD_DIR/$(basename "$f")"
    cp "$f" "$dest"; localize_agent_names "$dest"; record "$dest"; n_cmd=$((n_cmd+1))
  done
  ok "$n_cmd commands -> $CMD_DIR  (/bq:<name>)"

  # agents -> agents/bq/bq-<role>.md  (name: bq-<role>)
  mkdir -p "$AGENT_DIR"; record "$AGENT_DIR"
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
  mkdir -p "$SKILL_ROOT"
  local n_skill=0
  for d in "$REPO_DIR"/skills/*/; do
    [[ -d "$d" ]] || continue
    local base newname dest
    base="$(basename "$d")"
    newname="$(bq_name "$base")"
    dest="$SKILL_ROOT/$newname"
    rm -rf "$dest"
    cp -R "$d" "$dest"
    if [[ -f "$dest/SKILL.md" ]]; then
      set_skill_name "$dest/SKILL.md" "$newname"
      localize_agent_names "$dest/SKILL.md"
    fi
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
  # native plugin install first (no-op if not present)
  do_plugin_uninstall

  step "Uninstalling bq from $CLAUDE_DIR"
  local removed=0

  if [[ -f "$MANIFEST" ]]; then
    # remove in reverse so files go before their dirs
    while IFS= read -r p; do
      [[ -n "$p" ]] || continue
      if [[ -e "$p" ]]; then rm -rf "$p"; info "removed $p"; removed=1; fi
    done < <(tac "$MANIFEST" 2>/dev/null || tail -r "$MANIFEST")
    rm -f "$MANIFEST"
  else
    warn "No manifest found; falling back to known locations"
  fi

  # fallback / belt-and-suspenders for the known layout
  [[ -d "$CMD_DIR" ]]      && { rm -rf "$CMD_DIR";      info "removed $CMD_DIR";      removed=1; }
  [[ -d "$AGENT_DIR" ]]    && { rm -rf "$AGENT_DIR";    info "removed $AGENT_DIR";    removed=1; }
  [[ -d "$TEMPLATE_DIR" ]] && { rm -rf "$TEMPLATE_DIR"; info "removed $TEMPLATE_DIR"; removed=1; }
  for d in "$SKILL_ROOT"/bq-*/; do
    [[ -d "$d" ]] || continue
    rm -rf "$d"; info "removed $d"; removed=1
  done

  # tidy now-empty parent dirs we may have created
  rmdir "$CLAUDE_DIR/commands" "$CLAUDE_DIR/agents" 2>/dev/null || true

  [[ "$removed" -eq 1 ]] && ok "bq uninstalled" || info "Nothing to uninstall"
}

# --- status ------------------------------------------------------------------
do_status() {
  step "bq install status"

  # native plugin
  if have_claude_cli; then
    if plugin_installed; then
      ok "Plugin: installed via the claude CLI"
      claude plugin list 2>/dev/null | grep -i bq | sed 's/^/    /' || true
    else
      info "Plugin: not installed via the claude CLI"
    fi
  else
    info "Plugin: claude CLI not found on PATH"
  fi

  # manual copy
  if [[ -f "$MANIFEST" ]]; then
    local n_cmd n_agent n_skill
    n_cmd=$(ls "$CMD_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
    n_agent=$(ls "$AGENT_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
    n_skill=$(ls -d "$SKILL_ROOT"/bq-*/ 2>/dev/null | wc -l | tr -d ' ')
    ok "Manual: installed in $CLAUDE_DIR"
    info "commands:  $n_cmd  ($CMD_DIR)"
    info "agents:    $n_agent  ($AGENT_DIR)"
    info "skills:    $n_skill  ($SKILL_ROOT/bq-*)"
    [[ -d "$TEMPLATE_DIR" ]] && info "templates: $TEMPLATE_DIR"
    info "manifest:  $MANIFEST"
  else
    info "Manual: not installed (no manifest at $MANIFEST)"
  fi
}

# --- usage -------------------------------------------------------------------
usage() {
  sed -n '3,27p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

# --- main --------------------------------------------------------------------
case "${1:-install}" in
  install)      do_install ;;
  plugin)       do_plugin_install ;;
  manual)       do_manual_install ;;
  status)       do_status ;;
  uninstall)    do_uninstall ;;
  reinstall)    do_uninstall; do_install ;;
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
