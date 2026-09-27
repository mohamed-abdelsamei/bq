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
#   agents/<role>.md     -> <prompts>/bq-<role>.agent.md    (custom agent bq-<role>)
#   skills/<name>/       -> ~/.copilot/skills/bq-<name>/     (skill id bq-<name>)
#   skills/bq-team/      -> <prompts>/bq-team.instructions.md (always-on, applyTo '**')
#   templates/           -> ~/.copilot/bq-templates/         (home for init/onboard scaffolding)
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
#                               default: macOS ~/Library/Application Support/Code/User/prompts,
#                               Linux ${XDG_CONFIG_HOME:-~/.config}/Code/User/prompts,
#                               Windows (Git Bash/MSYS) $APPDATA/Code/User/prompts
#   COPILOT_SKILLS_DIR=/path    Copilot skills folder (default ~/.copilot/skills)

set -euo pipefail

# --- paths -------------------------------------------------------------------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# VS Code's per-user prompts folder for this OS
default_prompts_dir() {
  case "$(uname -s)" in
    Darwin) printf '%s' "$HOME/Library/Application Support/Code/User/prompts" ;;
    MINGW*|MSYS*|CYGWIN*)
      local appdata="${APPDATA:-$HOME/AppData/Roaming}"
      if command -v cygpath >/dev/null 2>&1; then appdata="$(cygpath -u "$appdata")"; fi
      printf '%s' "$appdata/Code/User/prompts" ;;
    *) printf '%s' "${XDG_CONFIG_HOME:-$HOME/.config}/Code/User/prompts" ;;
  esac
}
# make a dir override absolute (relative = from the current dir) with no ./ segments or trailing
# slash, so recorded manifest paths stay comparable in owned_path (which refuses /./ segments)
abs_dir() {
  local p="$1" dot="/./" sl="/"
  [[ "$p" == /* ]] || p="$PWD/$p"
  while [[ "$p" == */./* ]]; do p="${p//"$dot"/$sl}"; done
  while [[ "$p" == ?*/ ]]; do p="${p%/}"; done
  printf '%s' "$p"
}
PROMPTS_DIR="$(abs_dir "${COPILOT_PROMPTS_DIR:-$(default_prompts_dir)}")"
SKILLS_DIR="$(abs_dir "${COPILOT_SKILLS_DIR:-$HOME/.copilot/skills}")"
COPILOT_HOME="$(dirname "$SKILLS_DIR")"
MANIFEST="$COPILOT_HOME/.bq-copilot-install-manifest"
TEMPLATE_DIR="$COPILOT_HOME/bq-templates"

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
# exactly the templates dir, or a DIRECT bq-* child of the prompts/skills folders — never those
# shared folders themselves, never anything deeper (which could sit behind a symlink), never a
# `..` or `.` segment. Callers strip trailing slashes and unlink symlinks, never recurse into one.
# a recorded mkdir: entry is only trusted if it is one of our target dirs or an ancestor of one
# (exactly what `mkdir -p` creates) — a tampered manifest can't point rmdir anywhere else
created_dir() {
  local d="$1" root
  for root in "$PROMPTS_DIR" "$SKILLS_DIR" "$TEMPLATE_DIR"; do
    [[ "$root" == "$d" || "$root" == "$d"/* ]] && return 0
  done
  return 1
}

owned_path() {
  local p="$1" root rest
  [[ -n "$p" && "$p" != "/" ]] || return 1
  case "/$p/" in */../*|*/./*) return 1 ;; esac
  [[ "$p" == "$TEMPLATE_DIR" ]] && return 0
  for root in "$PROMPTS_DIR" "$SKILLS_DIR"; do
    case "$p" in "$root"/bq-*) rest="${p#"$root"/}"; [[ "$rest" != */* ]] && return 0 ;; esac
  done
  return 1
}

# delete an owned path: a symlink is unlinked (never followed), anything else removed recursively
remove_path() {
  if [[ -L "$1" ]]; then rm -f "$1"; elif [[ -e "$1" ]]; then rm -rf "$1"; else return 1; fi
  info "removed $1"
}

# --- transforms --------------------------------------------------------------
# Map Claude tool names to Copilot tool aliases, preserving order and de-duping.
map_tools() {
  local list="$1" t m seen="" out=""
  local IFS=','
  for t in $list; do
    t="${t//[[:space:]]/}"
    case "$t" in
      Read)       m="read" ;;
      Grep|Glob)  m="search" ;;
      Edit|Write) m="edit" ;;
      Bash)       m="execute" ;;
      WebFetch)   m="web" ;;
      Agent|Task) m="agent" ;;
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
# Agent/Task-tool/subagent_type phrasing -> Copilot agent wording. Plugin-scoped agent names
# (bq:<role>, no leading slash) become bq-<role> before /bq:<command> -> /bq-<command>. The
# Claude-only prose is wrapped in <!-- claude-only --> ... <!-- /claude-only --> markers (invisible
# when rendered) and resolved first: a span carrying `<!-- copilot: B -->` before its closer becomes
# B (empty B drops the span and its trailing blank line, keeping one paragraph break when the span
# ended a paragraph); a plain span is the "plugin vs manual"
# naming clause and becomes the single Copilot form. "the **bq-team** skill" -> instructions, since
# bq-team ships here as the always-on bq-team.instructions.md, not a skill.
rewrite_body() {
  perl -0777 -pe '
    # An empty-B span that ends a paragraph (its line follows a non-blank line, a blank line follows
    # it) keeps one newline, so a heading after it stays a separate block; an inline span keeps its
    # trailing newlines. $_ is still the unmodified input while s///g runs.
    sub dropped { my ($at, $nl) = @_; my $before = $at >= 2 ? substr($_, $at - 2, 2) : "\n\n";
      return $before =~ /\n$/ ? ($before eq "\n\n" || $nl ne "\n\n" ? "" : "\n") : $nl; }
    s{<!--\s*claude-only\s*-->\n?(?:(?!<!--\s*/?claude-only).)*?<!--\s*copilot:\s*((?:(?!-->).)*?)\s*-->\s*?<!--\s*/claude-only\s*-->(\n?\n?)}{length($1) ? "$1$2" : dropped($-[0], $2)}gse;
    s{<!--\s*claude-only\s*-->(?:(?!<!--\s*/?claude-only|<!--\s*copilot:).)*?<!--\s*/claude-only\s*-->}{`bq-<role>` (e.g. `bq-engineer`)}gs;
    s/\*\*bq-team\*\*(\s+)skill\x27s\b/**bq-team**$1instructions\x27/g;
    s/\*\*bq-team\*\*(\s+)skill\b/**bq-team**$1instructions/g;
    s/\b(Agent|Task)\s+tool(\*\*)?\s+\(formerly\s+Task\)/$1 tool$2/g;
    s/(?<![\/\w])bq:(maestro|architect|engineer|tester|reviewer|researcher|scribe)\b/bq-$1/g;
    s{/bq:}{/bq-}g;
    s/\*\*(maestro|architect|engineer|tester|reviewer|researcher|scribe)\b/**bq-$1/g;
    s/\*\*(memory|critique|facilitation|mr-review|debugging|research-method|feedback-loop|plugin-promotion|decision-and-spec|codebase-onboarding)\b/**bq-$1/g;
    s/`(?:Agent|Task)`\s+tool\b/agent tool/g;
    s/\bAgent-tool-based\b/agent-based/g;
    s/\b(?:Agent|Task)\s+tool\b/agent tool/g;
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

# agents/<role>.md -> a .agent.md: name bq-<role>, drop `model:`, map `tools:`, set `agents:`.
agent_to_agent() {
  local src="$1" dest="$2" agents_line="$3" name="$4" mapped=""
  local raw
  raw="$(sed -n 's/^tools:[[:space:]]*//p' "$src" | head -1)"
  mapped="$(map_tools "$raw")"
  awk -v tools="$mapped" -v agents="$agents_line" -v name="$name" '
    NR==1 && $0=="---" { fm=1; print; next }
    fm==1 && $0=="---" { print "tools: " tools; print agents; print; fm=0; next }
    fm==1 && /^name:/ { print "name: " name; next }
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
    NR==1 && $0=="---" { fm=1; print; next }
    fm==1 && $0=="---" { fm=0 }
    fm==1 && /^name:[[:space:]]/ { print "name: " n; fm=2; next }
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

# rewrite a file in place through rewrite_body
rewrite_file() {
  local file="$1" tmp
  tmp="$(mktemp)"
  rewrite_body < "$file" > "$tmp"
  mv "$tmp" "$file"
}

# point the installed bq-memory "Locating the templates" section at this install's templates only
# (no plugin root, no Claude plugin cache, no ~/.claude path in Copilot)
localize_memory_paths() {
  local file="$1" tmp
  [[ -f "$file" ]] || return 0
  tmp="$(mktemp)"
  TD="$TEMPLATE_DIR" perl -0777 -pe '
    s{(^\#\#\ Locating\ the\ templates\n).*?(?=^\#\#\ )}{$1\n`/bq-init` and `/bq-onboard` seed `<mem>/` from starter files (`README.md`, `charter.md`, the\nfolders). Use the first of these that exists:\n\n1. `$ENV{TD}/bq/` — installed by `install-copilot.sh`.\n2. Not found → generate the files directly from the **Layout** above and the **Templates** below.\n\n}ms;
  ' "$file" > "$tmp"
  mv "$tmp" "$file"
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
  # note the dirs this install creates (deepest first) so uninstall can remove them if left empty
  # (carrying over any recorded by a previous install, so re-running install doesn't forget them)
  local created=() d
  if [[ -f "$MANIFEST" ]]; then
    while IFS= read -r d; do
      [[ "$d" == mkdir:* ]] && created+=("${d#mkdir:}")
    done < "$MANIFEST"
  fi
  for d in "$PROMPTS_DIR" "$SKILLS_DIR"; do
    while [[ ! -e "$d" ]]; do created+=("$d"); d="$(dirname "$d")"; done
  done
  mkdir -p "$PROMPTS_DIR" "$SKILLS_DIR"
  : > "$MANIFEST"
  for d in ${created[@]+"${created[@]}"}; do record "mkdir:$d"; done

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

  # agents -> bq-<role>.agent.md
  local n_agent=0
  for f in "$REPO_DIR"/agents/*.md; do
    [[ -e "$f" ]] || continue
    local base dest agents_line
    base="$(basename "$f" .md)"
    dest="$PROMPTS_DIR/bq-$base.agent.md"
    if [[ "$base" == "maestro" ]]; then
      agents_line="agents: [bq-architect, bq-engineer, bq-tester, bq-reviewer, bq-researcher, bq-scribe]"
    else
      agents_line="agents: []"
    fi
    agent_to_agent "$f" "$dest" "$agents_line" "bq-$base"; record "$dest"; n_agent=$((n_agent+1))
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
    if [[ -f "$dest/SKILL.md" ]]; then set_skill_name "$dest/SKILL.md" "$newname"; fi
    local md
    while IFS= read -r md; do rewrite_file "$md"; done < <(find "$dest" -type f -name '*.md')
    record "$dest"; n_skill=$((n_skill+1))
  done
  ok "$n_skill skills -> $SKILLS_DIR/bq-*"

  # templates -> bq-templates/  (Copilot has no plugin root; bq-memory is pointed here)
  if [[ -d "$REPO_DIR/templates" ]]; then
    rm -rf "$TEMPLATE_DIR"
    cp -R "$REPO_DIR/templates" "$TEMPLATE_DIR"
    record "$TEMPLATE_DIR"
    local md
    while IFS= read -r md; do rewrite_file "$md"; done < <(find "$TEMPLATE_DIR" -type f -name '*.md')
    localize_memory_paths "$SKILLS_DIR/bq-memory/SKILL.md"
    ok "templates -> $TEMPLATE_DIR  (bq-memory lookup pointed at $TEMPLATE_DIR/bq/)"
  fi

  # always-on identity from the bq-team skill
  local team_src="$REPO_DIR/skills/bq-team/SKILL.md"
  if [[ -f "$team_src" ]]; then
    local inst="$PROMPTS_DIR/bq-team.instructions.md"
    gen_team_instructions "$team_src" "$inst"; record "$inst"
    ok "always-on identity -> $inst  (applyTo '**')"
  fi

  if ! do_verify; then
    warn "Installed, but verify found Claude-only leftovers (see above) — Copilot output may be wrong."
    exit 1
  fi

  step "Done"
  ok "Installed $n_agent agents, $n_cmd prompts, $n_skill skills"
  info "In Copilot Chat type '/' to run /bq-build, /bq-brainstorm, /bq-status …"
  info "Reload VS Code (Developer: Reload Window) to pick them up."
}

# --- uninstall ---------------------------------------------------------------
do_uninstall() {
  step "Uninstalling bq from GitHub Copilot"
  local removed=0

  local made=() p
  if [[ -f "$MANIFEST" ]]; then
    while IFS= read -r p; do
      [[ "$p" == mkdir:* ]] && made+=("${p#mkdir:}")
    done < "$MANIFEST"
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

  # fallback / belt-and-suspenders — only names this repo ships, so a user's own bq-* file is
  # never swept up
  local d s
  local known=("$PROMPTS_DIR/bq-team.instructions.md" "$TEMPLATE_DIR")
  for s in "$REPO_DIR"/commands/*.md; do
    [[ -e "$s" ]] && known+=("$PROMPTS_DIR/bq-$(basename "$s" .md).prompt.md")
  done
  for s in "$REPO_DIR"/agents/*.md; do
    [[ -e "$s" ]] && known+=("$PROMPTS_DIR/bq-$(basename "$s" .md).agent.md")
  done
  for s in "$REPO_DIR"/skills/*/; do
    [[ -d "$s" ]] && known+=("$SKILLS_DIR/$(bq_name "$(basename "$s")")")
  done
  for d in "${known[@]}"; do
    [[ -L "$d" || -e "$d" ]] || continue
    if remove_path "$d"; then removed=1; fi
  done

  # tidy only the dirs this install recorded as created — rmdir only succeeds on empty dirs, so
  # one now holding the user's own files stays; two passes so a parent listed before its child goes
  for d in ${made[@]+"${made[@]}"} ${made[@]+"${made[@]}"}; do
    created_dir "$d" || continue
    rmdir "$d" 2>/dev/null || true
  done

  if [[ "$removed" -eq 1 ]]; then ok "bq uninstalled from Copilot"; else info "Nothing to uninstall"; fi
}

# --- status ------------------------------------------------------------------
do_status() {
  step "bq Copilot install status"
  local n_prompt n_agent n_skill inst
  shopt -s nullglob
  n_prompt=$(count "$PROMPTS_DIR"/bq-*.prompt.md)
  n_agent=$(count "$PROMPTS_DIR"/bq-*.agent.md)
  n_skill=$(count "$SKILLS_DIR"/bq-*/)
  shopt -u nullglob
  inst="$PROMPTS_DIR/bq-team.instructions.md"

  if [[ -f "$MANIFEST" || "$n_prompt" -gt 0 ]]; then
    ok "Installed in your Copilot profile"
    info "prompts:   $n_prompt  ($PROMPTS_DIR/bq-*.prompt.md)"
    info "agents:    $n_agent  ($PROMPTS_DIR/bq-*.agent.md)"
    info "skills:    $n_skill  ($SKILLS_DIR/bq-*)"
    if [[ -d "$TEMPLATE_DIR" ]]; then info "templates: $TEMPLATE_DIR"; fi
    if [[ -f "$inst" ]]; then info "always-on: $inst"; fi
    if [[ -f "$MANIFEST" ]]; then info "manifest:  $MANIFEST"; fi
  else
    info "Not installed (no manifest at $MANIFEST)"
  fi
}

# --- verify ------------------------------------------------------------------
do_verify() {
  step "Verifying bq Copilot install"
  local files=() f d fail=0
  # only what this repo ships — a user's own bq-* file is not ours to judge
  local s
  for s in "$REPO_DIR"/commands/*.md; do
    f="$PROMPTS_DIR/bq-$(basename "$s" .md).prompt.md"; [[ -e "$f" ]] && files+=("$f")
  done
  for s in "$REPO_DIR"/agents/*.md; do
    f="$PROMPTS_DIR/bq-$(basename "$s" .md).agent.md"; [[ -e "$f" ]] && files+=("$f")
  done
  f="$PROMPTS_DIR/bq-team.instructions.md"; [[ -e "$f" ]] && files+=("$f")
  for s in "$REPO_DIR"/skills/*/; do
    d="$SKILLS_DIR/$(bq_name "$(basename "$s")")"
    while IFS= read -r f; do files+=("$f"); done < <(find "$d" -type f -name '*.md' 2>/dev/null)
  done
  while IFS= read -r f; do files+=("$f"); done < <(find "$TEMPLATE_DIR" -type f -name '*.md' 2>/dev/null)
  if [[ "${#files[@]}" -eq 0 ]]; then warn "Nothing installed to verify"; return 1; fi

  local f bad
  for f in "${files[@]}"; do
    bad="$(perl -0777 -ne '
      my @h;
      push @h, "/bq:" if m{/bq:};
      push @h, "bq:bq-" if /\bbq:bq-/;
      push @h, "bq:<role>" if m{(?<![/\w])bq:(?:maestro|architect|engineer|tester|reviewer|researcher|scribe)\b};
      push @h, "subagent_type" if /subagent_type/;
      push @h, "Task tool" if /\bTask\s+tool\b/;
      push @h, "`Agent` tool" if /`(?:Agent|Task)`\s+tool\b/;
      push @h, "Agent-tool" if /\bAgent-tool\b/;
      push @h, "installed as a plugin" if /installed\s+as\s+a\s+plugin/;
      push @h, "manual/global install" if /manual\/global\s+install/;
      push @h, "claude-only marker" if /claude-only/;
      push @h, "copilot: marker" if /<!--\s*copilot:/;
      print join(",", @h) if @h;
    ' "$f")"
    if [[ -n "$bad" ]]; then warn "leftover [$bad] in: $f"; fail=1; fi
    # bq-memory's template lookup is rewritten to the Copilot templates dir, so any plugin-root
    # reference left is drift in the source section (localize_memory_paths no longer matched it)
    if grep -q "CLAUDE_PLUGIN_ROOT" "$f"; then warn "leftover [\${CLAUDE_PLUGIN_ROOT}] in: $f"; fail=1; fi
  done

  for s in "$REPO_DIR"/commands/*.md; do
    f="$PROMPTS_DIR/bq-$(basename "$s" .md).prompt.md"
    [[ -e "$f" ]] || continue
    local av
    av="$(sed -n 's/^agent:[[:space:]]*//p' "$f" | head -1)"
    case "$av" in
      bq-maestro|bq-reviewer) ;;
      *) warn "$(basename "$f"): unexpected agent '$av'"; fail=1 ;;
    esac
  done

  if [[ "$fail" -eq 0 ]]; then
    ok "Verify passed: no /bq:, bq:bq-, bq:<role>, subagent_type, Task tool, backticked Agent tool, Agent-tool, plugin/manual naming clause, claude-only marker, or \${CLAUDE_PLUGIN_ROOT}; every prompt maps to a known agent"
    return 0
  fi
  warn "Verify found issues (see above)"
  return 1
}

# --- usage -------------------------------------------------------------------
# prints the leading comment block (line 2 up to the first non-comment line)
usage() {
  awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "${BASH_SOURCE[0]}"
}

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
