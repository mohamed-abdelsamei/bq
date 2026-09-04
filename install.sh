#!/usr/bin/env bash
#
# install.sh — install the "crew" agent team globally into ~/.claude,
# for environments where the Claude Code plugin/marketplace flow is unavailable.
#
# Namespacing (collision-proof, cleanly removable):
#   commands/<name>.md   -> ~/.claude/commands/crew/<name>.md   (invoked as /crew:<name>)
#   skills/<name>/       -> ~/.claude/skills/crew-<name>/        (skill id crew-<name>)
#   agents/<name>.md     -> ~/.claude/agents/crew/<name>.md      (name unchanged; delegation intact)
#   templates/           -> ~/.claude/crew-templates/            (home for init/onboard scaffolding)
#
# Usage:
#   ./install.sh install      Install (removes any legacy flat install first)
#   ./install.sh uninstall    Remove everything this script installed
#   ./install.sh reinstall    uninstall then install
#   ./install.sh clean-legacy Remove only the old flat/mis-nested install
#
# Target dir override: CLAUDE_CONFIG_DIR=/path ./install.sh install

set -euo pipefail

# --- paths -------------------------------------------------------------------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
MANIFEST="$CLAUDE_DIR/.crew-install-manifest"

CMD_DIR="$CLAUDE_DIR/commands/crew"
AGENT_DIR="$CLAUDE_DIR/agents/crew"
SKILL_ROOT="$CLAUDE_DIR/skills"
TEMPLATE_DIR="$CLAUDE_DIR/crew-templates"

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

  # flat agents: ~/.claude/agents/<name>.md
  for f in "$REPO_DIR"/agents/*.md; do
    [[ -e "$f" ]] || continue
    local legacy="$CLAUDE_DIR/agents/$(basename "$f")"
    if [[ -f "$legacy" ]]; then rm -f "$legacy"; info "removed $legacy"; removed=1; fi
  done

  # mis-nested skills: ~/.claude/skills/crew/<skill>/
  if [[ -d "$SKILL_ROOT/crew" ]]; then
    rm -rf "$SKILL_ROOT/crew"; info "removed $SKILL_ROOT/crew"; removed=1
  fi

  [[ "$removed" -eq 1 ]] && ok "Legacy install removed" || info "No legacy install found"
}

# --- skill name prefixing ----------------------------------------------------
# crew-team -> crew-team ; memory -> crew-memory
crew_name() {
  case "$1" in
    crew-*) printf 'crew-%s' "${1#crew-}" ;;  # normalize, no double prefix
    *)      printf 'crew-%s' "$1" ;;
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

# --- install -----------------------------------------------------------------
do_install() {
  require_claude_dir
  clean_legacy

  step "Installing crew into $CLAUDE_DIR"
  : > "$MANIFEST"   # fresh manifest

  # commands -> commands/crew/
  mkdir -p "$CMD_DIR"; record "$CMD_DIR"
  local n_cmd=0
  for f in "$REPO_DIR"/commands/*.md; do
    [[ -e "$f" ]] || continue
    local dest="$CMD_DIR/$(basename "$f")"
    cp "$f" "$dest"; record "$dest"; n_cmd=$((n_cmd+1))
  done
  ok "$n_cmd commands -> $CMD_DIR  (/crew:<name>)"

  # agents -> agents/crew/  (names unchanged)
  mkdir -p "$AGENT_DIR"; record "$AGENT_DIR"
  local n_agent=0
  for f in "$REPO_DIR"/agents/*.md; do
    [[ -e "$f" ]] || continue
    local dest="$AGENT_DIR/$(basename "$f")"
    cp "$f" "$dest"; record "$dest"; n_agent=$((n_agent+1))
  done
  ok "$n_agent agents -> $AGENT_DIR"

  # skills -> skills/crew-<name>/  (rewrite name: field)
  mkdir -p "$SKILL_ROOT"
  local n_skill=0
  for d in "$REPO_DIR"/skills/*/; do
    [[ -d "$d" ]] || continue
    local base newname dest
    base="$(basename "$d")"
    newname="$(crew_name "$base")"
    dest="$SKILL_ROOT/$newname"
    rm -rf "$dest"
    cp -R "$d" "$dest"
    [[ -f "$dest/SKILL.md" ]] && set_skill_name "$dest/SKILL.md" "$newname"
    record "$dest"; n_skill=$((n_skill+1))
  done
  ok "$n_skill skills -> $SKILL_ROOT/crew-*"

  # templates -> crew-templates/
  if [[ -d "$REPO_DIR/templates" ]]; then
    rm -rf "$TEMPLATE_DIR"
    cp -R "$REPO_DIR/templates" "$TEMPLATE_DIR"
    record "$TEMPLATE_DIR"
    ok "templates -> $TEMPLATE_DIR"

    # point init/onboard at the installed template home
    for c in init onboard; do
      local cf="$CMD_DIR/$c.md"
      [[ -f "$cf" ]] || continue
      local tmp; tmp="$(mktemp)"
      sed "s#this plugin's \`templates/crew/\`#\`$TEMPLATE_DIR/crew/\`#g" "$cf" > "$tmp"
      mv "$tmp" "$cf"
    done
    info "rewrote template path in init/onboard"
  fi

  step "Done"
  ok "Installed $n_agent agents, $n_cmd commands, $n_skill skills"
  info "Commands are namespaced: /crew:build, /crew:status, /crew:brainstorm …"
  info "Restart Claude Code (or reload) to pick them up."
}

# --- uninstall ---------------------------------------------------------------
do_uninstall() {
  step "Uninstalling crew from $CLAUDE_DIR"
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
  for d in "$SKILL_ROOT"/crew-*/; do
    [[ -d "$d" ]] || continue
    rm -rf "$d"; info "removed $d"; removed=1
  done

  # tidy now-empty parent dirs we may have created
  rmdir "$CLAUDE_DIR/commands" "$CLAUDE_DIR/agents" 2>/dev/null || true

  [[ "$removed" -eq 1 ]] && ok "crew uninstalled" || info "Nothing to uninstall"
}

# --- main --------------------------------------------------------------------
case "${1:-install}" in
  install)      do_install ;;
  uninstall)    do_uninstall ;;
  reinstall)    do_uninstall; do_install ;;
  clean-legacy) require_claude_dir; clean_legacy ;;
  -h|--help|help)
    sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    ;;
  *)
    warn "Unknown command: $1"
    info "Use: install | uninstall | reinstall | clean-legacy"
    exit 1
    ;;
esac
