#!/usr/bin/env bash
set -euo pipefail

# ─── Co-Agents Installer (GitHub Copilot) ────────────────────────────────────
# Installs the Copilot bundle (agents, prompts, instructions, skills) for VS Code.
# The repo files ARE the payload — no build step.
#
#   Global (default):  every workspace — as a managed plugin directory in your
#                      VS Code user profile, with discovery symlinks.
#   Project:           one repo — into <path>/.github/, tracked by a manifest.
#
# Needs: python3, bash. Run from a clone of the repo:
#   ./install.sh                 # global install (all workspaces)
#   ./install.sh --update        # refresh the managed global install
#   ./install.sh --uninstall     # remove the managed global install
#   ./install.sh --project .     # install into this repo's .github/
# ─────────────────────────────────────────────────────────────────────────────

REPO="mohamed-abdelsamei/co-agents"
PLUGIN_NAME="co-agents"
MANIFEST_NAME=".co-agents-plugin.json"
MARKER_NAME=".co-agents-managed"
COPILOT_PREFIX="ca-"

DRY_RUN=false
FORCE=false
UNINSTALL=false
PROJECT=""
USER_DIR=""
SCOPE="global"

RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'; BLUE=$'\033[0;34m'
BOLD=$'\033[1m'; NC=$'\033[0m'
log()  { echo -e "${GREEN}→${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*" >&2; }
info() { echo -e "${BLUE}ℹ${NC} $*"; }
dry()  { echo -e "${YELLOW}[dry-run]${NC} $*"; }

usage() {
  cat <<EOF
${BOLD}Co-Agents Installer — GitHub Copilot (VS Code)${NC}

${BOLD}Usage:${NC}
  ./install.sh [options]

${BOLD}Scope${NC} (default: global):
  (default)        Global — installs into your VS Code user profile, available in every workspace.
  --project PATH   Project — installs into PATH/.github/ and tracks files with a manifest.

${BOLD}Other:${NC}
  --update        Refresh an existing managed global install (adopts old flat files).
  --uninstall     Remove the managed install for the selected scope.
  --user-dir DIR   Override the VS Code user-profile directory (global scope).
  --dry-run        Preview without writing anything.
  --force          Overwrite existing files (default: skip files that exist).
  --help           Show this help.

${BOLD}Examples:${NC}
  ./install.sh                       # global, all workspaces
  ./install.sh --update              # update the managed global install
  ./install.sh --uninstall           # uninstall the managed global install
  ./install.sh --project ~/Work/app  # into that repo's .github/
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)  SCOPE="project"; PROJECT="${2:-}"; shift 2 ;;
    --user-dir) USER_DIR="${2:-}"; shift 2 ;;
    --update)   FORCE=true; shift ;;
    --uninstall) UNINSTALL=true; shift ;;
    --dry-run)  DRY_RUN=true; shift ;;
    --force)    FORCE=true; shift ;;
    --help|-h)  usage ;;
    *)          err "Unknown argument: $1"; echo ""; usage ;;
  esac
done

# ─── Locate repo + payload ────────────────────────────────────────────────────

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
[[ -d "$REPO_DIR/agents" ]] || { err "Run this from a clone of the co-agents repo."; exit 1; }
command -v python3 >/dev/null 2>&1 || { err "python3 is required."; exit 1; }

# The plugin payload is the repo itself — no build step; the files are the source of truth.
DIST="$REPO_DIR"
[[ -f "$DIST/copilot-instructions.md" ]] || { err "Missing payload: $DIST/copilot-instructions.md"; exit 1; }

# ─── Install helpers ──────────────────────────────────────────────────────────

copied=0; skipped=0
installed_files=()

relpath() {
  python3 - "$1" "$2" <<'PY'
import os
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
path = Path(os.path.abspath(sys.argv[2]))
path = path.parent.resolve() / path.name
try:
  rel = path.relative_to(root)
except ValueError:
  rel = Path(os.path.relpath(path, root))
print(rel.as_posix())
PY
}

copy_file() {
  local src="$1" dest="$2"
  if [[ -f "$dest" ]] && ! $FORCE; then warn "skip (exists): ${dest/#$HOME/\~}"; skipped=$((skipped+1)); return; fi
  if $DRY_RUN; then dry "→ ${dest/#$HOME/\~}"; else mkdir -p "$(dirname "$dest")"; cp "$src" "$dest"; fi
  installed_files+=("$dest")
  copied=$((copied+1))
}
copy_glob() { # copy_glob <src-dir> <glob> <dest-dir>
  local d="$1" g="$2" out="$3" f
  shopt -s nullglob
  for f in "$d"/$g; do copy_file "$f" "$out/$(basename "$f")"; done
  shopt -u nullglob
}
copy_tree_files() { # copy_tree_files <src-dir> <dest-dir>
  local src_dir="$1" dest_dir="$2" f rel
  [[ -d "$src_dir" ]] || return 0
  while IFS= read -r -d '' f; do
    rel="${f#"$src_dir"/}"
    copy_file "$f" "$dest_dir/$rel"
  done < <(find "$src_dir" -type f -print0)
}

copy_payload() { # copy_payload <dest> — copy only managed global plugin files
  local dest="$1" d
  if $DRY_RUN; then dry "sync plugin payload → ${dest/#$HOME/\~}/"; return; fi
  mkdir -p "$dest"
  for d in agents prompts instructions templates; do
    [[ -d "$DIST/$d" ]] && cp -R "$DIST/$d" "$dest/"
  done
  [[ -d "$DIST/skills" ]] && cp -R "$DIST/skills" "$dest/skills"
}

safe_rm() {
  local target="$1"
  if $DRY_RUN; then dry "remove ${target/#$HOME/\~}"; else rm -rf -- "$target"; fi
}

write_manifest() { # write_manifest <install-root> <manifest-path> <plugin-dir-or-empty> <files...>
  local root="$1" manifest="$2" plugin_dir="$3" file rels=()
  shift 3
  for file in "$@"; do rels+=("$(relpath "$root" "$file")"); done
  if $DRY_RUN; then dry "write manifest ${manifest/#$HOME/\~}"; return; fi
  python3 - "$root" "$manifest" "$plugin_dir" "$REPO" "${rels[@]}" <<'PY'
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
manifest_path = Path(sys.argv[2]).resolve()
plugin_arg = sys.argv[3]
plugin_dir = Path(plugin_arg).resolve() if plugin_arg else None
files = sys.argv[5:]

data = {
    "name": "co-agents",
    "type": "copilot-plugin",
    "managedBy": "install.sh",
    "repository": sys.argv[4],
    "installedAt": datetime.now(timezone.utc).isoformat(),
    "files": files,
}
if plugin_dir is not None:
    try:
        data["pluginDir"] = plugin_dir.relative_to(root).as_posix()
    except ValueError:
        data["pluginDir"] = Path(os.path.relpath(plugin_dir, root)).as_posix()
manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

remove_managed_install() { # remove_managed_install <install-root> <manifest-path>
  local root="$1" manifest="$2"
  [[ -f "$manifest" ]] || return 1
  python3 - "$root" "$manifest" "$DRY_RUN" <<'PY'
import json
import os
from pathlib import Path
import shutil
import sys

root = Path(sys.argv[1]).resolve()
manifest = Path(sys.argv[2]).resolve()
dry_run = sys.argv[3] == "true"
data = json.loads(manifest.read_text(encoding="utf-8"))

if data.get("name") != "co-agents" or data.get("managedBy") != "install.sh":
    raise SystemExit(f"Refusing to use unrecognized manifest: {manifest}")

skill_root = Path.home() / ".copilot" / "skills"

def inside_root(path: Path) -> Path:
    path = Path(os.path.abspath(path))
    path = path.parent.resolve() / path.name
    try:
        path.relative_to(root)
    except ValueError:
        path.relative_to(skill_root)
    return path

def inside_plugin_root(path: Path) -> Path:
    path = path.resolve()
    for allowed_root in (root, root.parent):
        try:
            path.relative_to(allowed_root)
            return path
        except ValueError:
            pass
    raise ValueError(f"Refusing path outside managed roots: {path}")

removal_rels = list(data.get("files", []))

plugin_rel = data.get("pluginDir")
plugin_dir = None
if plugin_rel:
    plugin_dir = inside_plugin_root(root / plugin_rel)
    marker = plugin_dir / ".co-agents-managed"
    if plugin_dir.exists():
        if not marker.exists():
            raise SystemExit(f"Refusing to remove unmarked plugin directory: {plugin_dir}")
        # Older installs may have skipped root discovery files that already existed.
        # Once a managed plugin exists, these payload basenames are owned by uninstall too.
        for pattern in ("agents/*.agent.md", "prompts/*.prompt.md", "instructions/*.instructions.md"):
            for owned_file in plugin_dir.glob(pattern):
                basename = owned_file.name
                removal_rels.append(basename)
                if basename.startswith("ca-"):
                    removal_rels.append(basename[len("ca-"):])

seen = set()
for rel in removal_rels:
    if rel in seen:
        continue
    seen.add(rel)
    path = inside_root(root / rel)
    if path.exists() or path.is_symlink():
        print(f"remove {path}")
        if not dry_run:
            path.unlink()

if plugin_dir and plugin_dir.exists():
    print(f"remove {plugin_dir}")
    if not dry_run:
        shutil.rmtree(plugin_dir)

print(f"remove {manifest}")
if not dry_run:
    manifest.unlink(missing_ok=True)
PY
}

install_global_plugin() { # install_global_plugin <prompts-dir>
  local prompts_dir="$1"
  local user_dir legacy_plugin_dir legacy_marker
  if [[ -d "$prompts_dir/.." ]]; then
    user_dir="$(cd "$prompts_dir/.." && pwd)"
  else
    user_dir="$(python3 - "$prompts_dir/.." <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).expanduser().resolve(strict=False))
PY
)"
  fi
  local plugin_dir="$user_dir/$PLUGIN_NAME"
  local skills_dir="$HOME/.copilot/skills"
  legacy_plugin_dir="$prompts_dir/$PLUGIN_NAME"
  local manifest="$prompts_dir/$MANIFEST_NAME"
  local marker="$plugin_dir/$MARKER_NAME" src target dest legacy_dest legacy_team_dest rel basename skill_name
  local migrate_legacy=false

  if [[ -f "$manifest" ]]; then
    log "Removing previous managed install..."
    migrate_legacy=true
    remove_managed_install "$prompts_dir" "$manifest"
  elif [[ -e "$plugin_dir" ]] && [[ ! -f "$marker" ]] && ! $FORCE; then
    err "Refusing to replace unmarked directory: ${plugin_dir/#$HOME/\~}"
    info "Move it aside or rerun with --force if it is an old co-agents install."
    exit 1
  elif [[ -e "$plugin_dir" ]]; then
    warn "Replacing ${plugin_dir/#$HOME/\~}"
    safe_rm "$plugin_dir"
  fi

  legacy_marker="$legacy_plugin_dir/$MARKER_NAME"
  if [[ "$legacy_plugin_dir" != "$plugin_dir" && ( -e "$legacy_plugin_dir" || -L "$legacy_plugin_dir" ) ]]; then
    if [[ -f "$legacy_marker" ]] || $FORCE; then
      warn "removing legacy managed plugin directory: ${legacy_plugin_dir/#$HOME/\~}"
      safe_rm "$legacy_plugin_dir"
    else
      err "Refusing to replace unmarked legacy directory: ${legacy_plugin_dir/#$HOME/\~}"
      info "Move it aside or rerun with --force if it is an old co-agents install."
      exit 1
    fi
  fi

  log "Installing managed plugin into ${plugin_dir/#$HOME/\~}/ ..."
  copy_payload "$plugin_dir"
  if ! $DRY_RUN; then touch "$marker"; fi

  shopt -s nullglob
  for src in "$DIST"/agents/*.agent.md "$DIST"/prompts/*.prompt.md "$DIST"/instructions/*.instructions.md; do
    rel="${src#"$DIST"/}"
    target="$plugin_dir/$rel"
    basename="$(basename "$target")"
    dest="$prompts_dir/$basename"
    if [[ "$basename" == "$COPILOT_PREFIX"* ]]; then
      legacy_dest="$prompts_dir/${basename#"$COPILOT_PREFIX"}"
      if [[ "$legacy_dest" != "$dest" && ( -e "$legacy_dest" || -L "$legacy_dest" ) ]]; then
        if $migrate_legacy || $FORCE; then
          warn "removing legacy discovery file: ${legacy_dest/#$HOME/\~}"
          safe_rm "$legacy_dest"
        else
          warn "legacy discovery file remains: ${legacy_dest/#$HOME/\~} (use --update to remove it)"
        fi
      fi
      legacy_team_dest=""
      if [[ "$basename" == "${COPILOT_PREFIX}"*.prompt.md ]]; then
        legacy_team_dest="$prompts_dir/${basename/#$COPILOT_PREFIX/${COPILOT_PREFIX}team-}"
      elif [[ "$basename" == "${COPILOT_PREFIX}memory.instructions.md" ]]; then
        legacy_team_dest="$prompts_dir/${COPILOT_PREFIX}team-""memory.instructions.md"
      fi
      if [[ -n "$legacy_team_dest" && "$legacy_team_dest" != "$dest" && ( -e "$legacy_team_dest" || -L "$legacy_team_dest" ) ]]; then
        if $migrate_legacy || $FORCE; then
          warn "removing legacy discovery file: ${legacy_team_dest/#$HOME/\~}"
          safe_rm "$legacy_team_dest"
        else
          warn "legacy discovery file remains: ${legacy_team_dest/#$HOME/\~} (use --update to remove it)"
        fi
      fi
    fi
    if [[ -e "$dest" || -L "$dest" ]]; then
      if [[ -L "$dest" ]] && [[ "$(readlink "$dest")" == "$target" ]]; then
        safe_rm "$dest"
      elif [[ -f "$dest" ]] && cmp -s "$dest" "$src"; then
        warn "adopting legacy flat file: ${dest/#$HOME/\~}"
        safe_rm "$dest"
      elif $FORCE; then
        warn "replacing existing discovery file: ${dest/#$HOME/\~}"
        safe_rm "$dest"
      else
        warn "skip (exists): ${dest/#$HOME/\~}"
        skipped=$((skipped+1))
        continue
      fi
    fi
    if $DRY_RUN; then dry "link ${dest/#$HOME/\~} → ${target/#$HOME/\~}"; else ln -s "$target" "$dest"; fi
    installed_files+=("$dest")
    copied=$((copied+1))
  done
  shopt -u nullglob

  if [[ -d "$DIST/skills" ]]; then
    if $DRY_RUN; then dry "ensure ${skills_dir/#$HOME/\~}/"; else mkdir -p "$skills_dir"; fi
    shopt -s nullglob
    for src in "$DIST"/skills/*; do
      [[ -d "$src" ]] || continue
      skill_name="$(basename "$src")"
      target="$plugin_dir/skills/$skill_name"
      dest="$skills_dir/$skill_name"
      if [[ -e "$dest" || -L "$dest" ]]; then
        if [[ -L "$dest" ]] && [[ "$(readlink "$dest")" == "$target" ]]; then
          safe_rm "$dest"
        elif $FORCE; then
          warn "replacing existing skill: ${dest/#$HOME/\~}"
          safe_rm "$dest"
        else
          warn "skip (exists): ${dest/#$HOME/\~}"
          skipped=$((skipped+1))
          continue
        fi
      fi
      if $DRY_RUN; then dry "link ${dest/#$HOME/\~} → ${target/#$HOME/\~}"; else ln -s "$target" "$dest"; fi
      installed_files+=("$dest")
      copied=$((copied+1))
    done
    shopt -u nullglob
  fi

  write_manifest "$prompts_dir" "$manifest" "$plugin_dir" "${installed_files[@]}"
}

default_vscode_user_dir() {
  case "$(uname -s)" in
    Darwin) echo "$HOME/Library/Application Support/Code/User" ;;
    Linux)  echo "$HOME/.config/Code/User" ;;
    *)      echo "" ;;
  esac
}

echo ""
echo -e "${BOLD}Co-Agents → GitHub Copilot${NC}"
echo -e "Scope: ${BLUE}$SCOPE${NC}   $($DRY_RUN && echo "${YELLOW}(dry-run)${NC}")"
echo ""

if [[ "$SCOPE" == "global" ]]; then
  # ── Global: VS Code user profile. Keep one managed plugin directory and expose
  #    root-level symlinks so VS Code's default user prompt discovery still works.
  [[ -n "$USER_DIR" ]] || USER_DIR="$(default_vscode_user_dir)"
  [[ -n "$USER_DIR" ]] || { err "Could not detect a VS Code user dir; pass --user-dir DIR."; exit 1; }
  DEST="$USER_DIR/prompts"
  if $DRY_RUN; then dry "ensure ${DEST/#$HOME/\~}/"; else mkdir -p "$DEST"; fi
  if $UNINSTALL; then
    log "Uninstalling managed plugin from ${DEST/#$HOME/\~}/ ..."
    if ! remove_managed_install "$DEST" "$DEST/$MANIFEST_NAME"; then
      warn "No managed co-agents install manifest found at ${DEST/#$HOME/\~}/$MANIFEST_NAME"
      info "For old flat installs, rerun ./install.sh --update once to adopt them, then ./install.sh --uninstall."
    fi
  else
    install_global_plugin "$DEST"
  fi
  echo ""
  info "Managed plugin: ${USER_DIR/#$HOME/\~}/$PLUGIN_NAME/"
  info "Discovery shims: ${DEST/#$HOME/\~}/$COPILOT_PREFIX<name>.agent.md, .prompt.md, .instructions.md"
  info "Skills: ~/.copilot/skills/<name>"
  info "Memory is per-project — run /ca-init inside a project to scaffold .coagents/."
else
  # ── Project: install the team tooling into <path>/.github/.
  #    Memory (.coagents/) is created later by /ca-init (new) or /ca-onboard (existing) —
  #    those build a real, filled-in charter, so we don't pre-scaffold a blank one here.
  [[ -n "$PROJECT" ]] || { err "--project needs a path."; exit 1; }
  [[ -d "$PROJECT" ]] || { err "No such directory: $PROJECT"; exit 1; }
  PROJECT="$(cd "$PROJECT" && pwd)"
  GH="$PROJECT/.github"
  if $UNINSTALL; then
    log "Uninstalling managed project files from ${PROJECT}/.github/ ..."
    if ! remove_managed_install "$PROJECT" "$GH/$MANIFEST_NAME"; then
      warn "No managed co-agents install manifest found at ${GH/#$HOME/\~}/$MANIFEST_NAME"
    fi
  else
    if [[ -f "$GH/$MANIFEST_NAME" ]]; then
      log "Removing previous managed project install..."
      remove_managed_install "$PROJECT" "$GH/$MANIFEST_NAME"
    fi

    log "Installing the team into ${PROJECT}/.github/ ..."
    copy_glob "$DIST/agents"  "*.agent.md"  "$GH/agents"
    copy_glob "$DIST/prompts" "*.prompt.md" "$GH/prompts"
    copy_tree_files "$DIST/skills" "$GH/skills"
    # All skill instructions (memory + the method skills), but NOT the global-only conductor
    # variant (co-core.instructions.md) — project scope uses copilot-instructions.md instead.
    shopt -s nullglob
    for f in "$DIST/instructions"/*.instructions.md; do
      [[ "$(basename "$f")" == "${COPILOT_PREFIX}core.instructions.md" ]] && continue
      copy_file "$f" "$GH/instructions/$(basename "$f")"
    done
    shopt -u nullglob
    # Preserve any existing copilot-instructions.md — it's the project's, and authoritative.
    if [[ -f "$GH/copilot-instructions.md" ]] && ! $FORCE; then
      warn "keeping your existing .github/copilot-instructions.md (the team will read, not replace it)"
    else
      copy_file "$DIST/copilot-instructions.md" "$GH/copilot-instructions.md"
    fi
    write_manifest "$PROJECT" "$GH/$MANIFEST_NAME" "" "${installed_files[@]}"
  fi
  echo ""
  if ! $UNINSTALL; then
    info "No project memory created yet. Inside this repo, run:"
    info "  /ca-init      — new project (interview → charter)"
    info "  /ca-onboard   — existing project (scan & understand, then build memory)"
    info "  /ca-knowledge — build/refresh the local concept map"
    info "  /ca-retro     — capture reusable lessons from experience"
  fi
fi

echo ""
echo -e "${BOLD}Summary${NC}  copied: $copied   skipped: $skipped"
if $DRY_RUN; then
  info "Dry run — re-run without --dry-run to apply."
elif $UNINSTALL; then
  echo -e "${GREEN}${BOLD}✓ Uninstalled.${NC}"
else
  echo -e "${GREEN}${BOLD}✓ Installed.${NC}"
  echo -e "Open Copilot Chat, pick the ${BOLD}ca-maestro${NC} agent (or a specialist), or run ${BOLD}/ca-brainstorm${NC}."
fi
