#!/usr/bin/env bash
#
# install-copilot.sh — install the "bq" agent team into GitHub Copilot (VS Code).
#
# Copilot has no plugin marketplace, so this transforms the canonical Claude files
# (agents/, commands/, skills/) into Copilot customization files at install time and
# copies them into your user profile. The Claude files stay the single source of truth.
#
# What it installs (user/global scope):
#   commands/<name>.md   -> <prompts>/bq-<name>.prompt.md   (invoked as /bq-<name>)
#   agents/bq-<name>.md  -> <prompts>/bq-<name>.agent.md    (custom agent bq-<name>)
#   skills/<name>/       -> ~/.copilot/skills/bq-<name>/     (skill id bq-<name>)
#   skills/bq-team/      -> <prompts>/bq-team.instructions.md (always-on, applyTo '**')
#
# Usage:
#   ./install-copilot.sh install      Transform + install into your Copilot profile
#   ./install-copilot.sh status       Show what is currently installed
#   ./install-copilot.sh uninstall    Remove everything this script installed
#   ./install-copilot.sh reinstall    uninstall then install
#   ./install-copilot.sh verify       Check installed files for leftover Claude-isms
#
# Overrides:
#   COPILOT_PROMPTS_DIR=/path   VS Code User prompts folder (holds *.prompt.md/*.agent.md/*.instructions.md)
#   COPILOT_SKILLS_DIR=/path    Copilot skills folder (default ~/.copilot/skills)

set -euo pipefail

# --- paths -------------------------------------------------------------------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="${COPILOT_PROMPTS_DIR:-$HOME/Library/Application Support/Code/User/prompts}"
SKILLS_DIR="${COPILOT_SKILLS_DIR:-$HOME/.copilot/skills}"
MANIFEST="$(dirname "$SKILLS_DIR")/.bq-copilot-install-manifest"

# --- pretty output -----------------------------------------------------------
info()  { printf '  %s\n' "$*"; }
step()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()    { printf '\033[32m✓ %s\033[0m\n' "$*"; }
warn()  { printf '\033[33m! %s\033[0m\n' "$*"; }

record() { printf '%s\n' "$1" >> "$MANIFEST"; }

# --- transforms --------------------------------------------------------------
# Map Claude tool names to Copilot tool aliases, preserving order and de-duping.
map_tools() {
  local list="$1" t m seen="" out=""
  local IFS=','
  for t in $list; do
    t="${t//[[:space:]]/}"
    case "$t" in
      Read)      m=read ;;
      Grep|Glob) m=search ;;
      Edit|Write) m=edit ;;
      Bash)      m=execute ;;
      WebFetch)  m=web ;;
      TodoWrite) m=todo ;;
      Task)      m=agent ;;
      *)         m="" ;;
    esac
    [[ -z "$m" ]] && continue
    case " $seen " in *" $m "*) continue ;; esac
    seen="$seen $m"
    out="${out:+$out,}$m"
  done
  printf '[%s]' "$out"
}

# Rewrite Claude-native body prose into Copilot form. perl -0777 slurps so phrases that
# wrap across a line break (e.g. "Task\ntool") still match. \b needs perl (BSD sed lacks it).
# Colon commands -> dash; bare specialist/skill names -> bq-prefixed (bolded tokens only);
# Task-tool/subagent_type phrasing -> Copilot agent wording.
rewrite_body() {
  perl -0777 -pe '
    s{/bq:}{/bq-}g;
    s/\*\*(architect|engineer|tester|reviewer|researcher|scribe)\b/**bq-$1/g;
    s/\*\*(memory|critique|facilitation|mr-review|debugging|research-method|feedback-loop|decision-and-spec|codebase-onboarding)\b/**bq-$1/g;
    s/\bTask\s+tool\b/agent tool/g;
    s/\bsubagent_type\b/agent/g;
  '
}

# commands/<name>.md -> a .prompt.md: run it in its owning bq agent, rewrite $ARGUMENTS.
cmd_to_prompt() {
  awk -v agent="$3" '
    NR==1 && $0=="---" { fm=1; print; next }
    fm==1 && $0=="---" { print "agent: " agent; print; fm=0; next }
    { line=$0; gsub(/\$ARGUMENTS/, "${input:args}", line); print line }
  ' "$1" | rewrite_body > "$2"
}

# agents/bq-<name>.md -> a .agent.md: drop `model:`, map `tools:`, set `agents:`.
agent_to_agent() {
  local src="$1" dest="$2" agents_line="$3" mapped=""
  local raw
  raw="$(sed -n 's/^tools:[[:space:]]*//p' "$src" | head -1)"
  mapped="$(map_tools "$raw")"
  awk -v tools="$mapped" -v agents="$agents_line" '
    NR==1 && $0=="---" { fm=1; print; next }
    fm==1 && $0=="---" { print "tools: " tools; print agents; print; fm=0; next }
    fm==1 && /^model:/ { next }
    fm==1 && /^tools:/ { next }
    { print }
  ' "$src" | rewrite_body > "$dest"
}

# skills/*/SKILL.md name: rewrite (bq-<name>), matching the Claude installer.
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

# skills/bq-team/SKILL.md -> always-on instructions (applyTo '**').
gen_team_instructions() {
  local src="$1" dest="$2" desc body_tmp
  desc="$(sed -n 's/^description:[[:space:]]*//p' "$src" | head -1)"
  body_tmp="$(mktemp)"
  awk '/^---[[:space:]]*$/ { n++; next } n>=2 { print }' "$src" > "$body_tmp"
  {
    printf '%s\n' '---'
    printf 'description: %s\n' "$desc"
    printf "applyTo: '**'\n"
    printf '%s\n' '---'
    rewrite_body < "$body_tmp"
  } > "$dest"
  rm -f "$body_tmp"
}

# bq-team -> bq-team ; memory -> bq-memory
bq_name() {
  case "$1" in
    bq-*) printf 'bq-%s' "${1#bq-}" ;;
    *)    printf 'bq-%s' "$1" ;;
  esac
}

# --- install -----------------------------------------------------------------
do_install() {
  step "Installing bq into GitHub Copilot"
  info "prompts: $PROMPTS_DIR"
  info "skills:  $SKILLS_DIR"
  mkdir -p "$PROMPTS_DIR" "$SKILLS_DIR"
  : > "$MANIFEST"

  # commands -> bq-<name>.prompt.md (run in the command's owning bq agent)
  local n_cmd=0
  for f in "$REPO_DIR"/commands/*.md; do
    [[ -e "$f" ]] || continue
    local base dest owner
    base="$(basename "$f" .md)"
    dest="$PROMPTS_DIR/bq-$base.prompt.md"
    case "$base" in
      grill) owner="bq-reviewer" ;;
      *)     owner="bq-maestro" ;;
    esac
    cmd_to_prompt "$f" "$dest" "$owner"; record "$dest"; n_cmd=$((n_cmd+1))
  done
  ok "$n_cmd commands -> $PROMPTS_DIR/bq-*.prompt.md  (/bq-<name>)"

  # agents -> bq-<name>.agent.md
  local n_agent=0
  for f in "$REPO_DIR"/agents/*.md; do
    [[ -e "$f" ]] || continue
    local base dest agents_line
    base="$(basename "$f" .md)"
    dest="$PROMPTS_DIR/$base.agent.md"
    if [[ "$base" == "bq-maestro" ]]; then
      agents_line="agents: [bq-architect, bq-engineer, bq-tester, bq-reviewer, bq-researcher, bq-scribe]"
    else
      agents_line="agents: []"
    fi
    agent_to_agent "$f" "$dest" "$agents_line"; record "$dest"; n_agent=$((n_agent+1))
  done
  ok "$n_agent agents -> $PROMPTS_DIR/bq-*.agent.md"

  # skills -> ~/.copilot/skills/bq-<name>/  (bq-team ships as the always-on instructions file instead)
  local n_skill=0
  for d in "$REPO_DIR"/skills/*/; do
    [[ -d "$d" ]] || continue
    local basedir newname dest
    basedir="$(basename "$d")"
    [[ "$basedir" == "bq-team" ]] && continue
    newname="$(bq_name "$basedir")"
    dest="$SKILLS_DIR/$newname"
    rm -rf "$dest"
    cp -R "$d" "$dest"
    if [[ -f "$dest/SKILL.md" ]]; then
      set_skill_name "$dest/SKILL.md" "$newname"
      local skill_tmp; skill_tmp="$(mktemp)"
      rewrite_body < "$dest/SKILL.md" > "$skill_tmp" && mv "$skill_tmp" "$dest/SKILL.md"
    fi
    record "$dest"; n_skill=$((n_skill+1))
  done
  ok "$n_skill skills -> $SKILLS_DIR/bq-*"

  # always-on identity from the bq-team skill
  local team_src="$REPO_DIR/skills/bq-team/SKILL.md"
  if [[ -f "$team_src" ]]; then
    local inst="$PROMPTS_DIR/bq-team.instructions.md"
    gen_team_instructions "$team_src" "$inst"; record "$inst"
    ok "always-on identity -> $inst  (applyTo '**')"
  fi

  do_verify || warn "post-install verify reported issues — see above"

  step "Done"
  ok "Installed $n_agent agents, $n_cmd prompts, $n_skill skills"
  info "In Copilot Chat type '/' to run /bq-build, /bq-brainstorm, /bq-status …"
  info "Reload VS Code (Developer: Reload Window) to pick them up."
}

# --- uninstall ---------------------------------------------------------------
do_uninstall() {
  step "Uninstalling bq from GitHub Copilot"
  local removed=0

  if [[ -f "$MANIFEST" ]]; then
    while IFS= read -r p; do
      [[ -n "$p" ]] || continue
      if [[ -e "$p" ]]; then rm -rf "$p"; info "removed $p"; removed=1; fi
    done < <(tac "$MANIFEST" 2>/dev/null || tail -r "$MANIFEST")
    rm -f "$MANIFEST"
  else
    warn "No manifest found; falling back to known locations"
  fi

  # fallback / belt-and-suspenders
  for f in "$PROMPTS_DIR"/bq-*.prompt.md "$PROMPTS_DIR"/bq-*.agent.md "$PROMPTS_DIR"/bq-team.instructions.md; do
    [[ -e "$f" ]] || continue
    rm -f "$f"; info "removed $f"; removed=1
  done
  for d in "$SKILLS_DIR"/bq-*/; do
    [[ -d "$d" ]] || continue
    rm -rf "$d"; info "removed $d"; removed=1
  done

  [[ "$removed" -eq 1 ]] && ok "bq uninstalled from Copilot" || info "Nothing to uninstall"
}

# --- status ------------------------------------------------------------------
do_status() {
  step "bq Copilot install status"
  local n_prompt n_agent n_skill inst
  n_prompt=$(ls "$PROMPTS_DIR"/bq-*.prompt.md 2>/dev/null | wc -l | tr -d ' ')
  n_agent=$(ls "$PROMPTS_DIR"/bq-*.agent.md 2>/dev/null | wc -l | tr -d ' ')
  n_skill=$(ls -d "$SKILLS_DIR"/bq-*/ 2>/dev/null | wc -l | tr -d ' ')
  inst="$PROMPTS_DIR/bq-team.instructions.md"

  if [[ -f "$MANIFEST" || "$n_prompt" -gt 0 ]]; then
    ok "Installed in your Copilot profile"
    info "prompts:   $n_prompt  ($PROMPTS_DIR/bq-*.prompt.md)"
    info "agents:    $n_agent  ($PROMPTS_DIR/bq-*.agent.md)"
    info "skills:    $n_skill  ($SKILLS_DIR/bq-*)"
    [[ -f "$inst" ]] && info "always-on: $inst"
    [[ -f "$MANIFEST" ]] && info "manifest:  $MANIFEST"
  else
    info "Not installed (no manifest at $MANIFEST)"
  fi
}

# --- verify ------------------------------------------------------------------
do_verify() {
  step "Verifying bq Copilot install"
  local files=() f d fail=0
  for f in "$PROMPTS_DIR"/bq-*.prompt.md "$PROMPTS_DIR"/bq-*.agent.md "$PROMPTS_DIR"/bq-team.instructions.md; do
    [[ -e "$f" ]] && files+=("$f")
  done
  for d in "$SKILLS_DIR"/bq-*/; do
    [[ -f "$d/SKILL.md" ]] && files+=("$d/SKILL.md")
  done
  if [[ "${#files[@]}" -eq 0 ]]; then warn "Nothing installed to verify"; return 1; fi

  local f bad
  for f in "${files[@]}"; do
    bad="$(perl -0777 -ne '
      my @h;
      push @h, "/bq:" if m{/bq:};
      push @h, "subagent_type" if /subagent_type/;
      push @h, "Task tool" if /\bTask\s+tool\b/;
      print join(",", @h) if @h;
    ' "$f")"
    if [[ -n "$bad" ]]; then warn "leftover [$bad] in: $f"; fail=1; fi
  done

  for f in "$PROMPTS_DIR"/bq-*.prompt.md; do
    [[ -e "$f" ]] || continue
    local av
    av="$(sed -n 's/^agent:[[:space:]]*//p' "$f" | head -1)"
    case "$av" in
      bq-maestro|bq-reviewer) ;;
      *) warn "$(basename "$f"): unexpected agent '$av'"; fail=1 ;;
    esac
  done

  if [[ "$fail" -eq 0 ]]; then
    ok "Verify passed: no /bq:, subagent_type, or Task tool; every prompt maps to a known agent"
    return 0
  fi
  warn "Verify found issues (see above)"
  return 1
}

# --- usage -------------------------------------------------------------------
usage() { sed -n '3,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

# --- main --------------------------------------------------------------------
case "${1:-install}" in
  install)   do_install ;;
  status)    do_status ;;
  uninstall) do_uninstall ;;
  reinstall) do_uninstall; do_install ;;
  verify)    do_verify ;;
  -h|--help|help) usage ;;
  *)
    warn "Unknown command: $1"
    info "Use: install | status | uninstall | reinstall | verify"
    exit 1
    ;;
esac
