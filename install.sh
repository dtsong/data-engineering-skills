#!/usr/bin/env bash
set -euo pipefail

# Data Engineering Skills Installer
# Installs skills to ~/.claude/skills/data-engineering-skills/

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="$HOME/.claude/skills/data-engineering-skills"
REPO_URL="https://github.com/dtsong/data-engineering-skills"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Available skills
ALL_SKILLS=(
  "dbt-skill"
  "integration-patterns-skill"
  "streaming-data-skill"
  "data-orchestration-skill"
  "python-data-engineering-skill"
  "ai-data-integration-skill"
)

# Currently available skills (others are planned)
AVAILABLE_SKILLS=(
  "dbt-skill"
  "integration-patterns-skill"
  "streaming-data-skill"
  "data-orchestration-skill"
)

# Role-based presets
declare -A ROLE_SKILLS
ROLE_SKILLS[analytics-engineer]="dbt-skill,python-data-engineering-skill"
ROLE_SKILLS[data-platform-engineer]="dbt-skill,integration-patterns-skill,streaming-data-skill,data-orchestration-skill,python-data-engineering-skill,ai-data-integration-skill"
ROLE_SKILLS[integration-engineer]="integration-patterns-skill,streaming-data-skill,data-orchestration-skill"
ROLE_SKILLS[ml-engineer]="python-data-engineering-skill,ai-data-integration-skill"

# Helper functions
info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
  echo -e "${RED}[ERROR]${NC} $1"
  exit 1
}

show_help() {
  cat << EOF
Data Engineering Skills Installer

USAGE:
  ./install.sh [OPTIONS]

OPTIONS:
  (no options)           Install all available skills
  --role ROLE            Install role-based preset
  --skills SKILLS        Install specific skills (comma-separated)
  --list                 List available skills and roles
  --update               Update existing installation (git pull)
  --help                 Show this help message

ROLES:
  analytics-engineer     dbt-skill, python-data-engineering-skill
  data-platform-engineer All skills (full toolkit)
  integration-engineer   integration-patterns-skill, streaming-data-skill, data-orchestration-skill
  ml-engineer            python-data-engineering-skill, ai-data-integration-skill

EXAMPLES:
  ./install.sh
    Install all available skills

  ./install.sh --role analytics-engineer
    Install dbt-skill and python-data-engineering-skill

  ./install.sh --skills dbt-skill,streaming-data-skill
    Install only dbt-skill and streaming-data-skill

  ./install.sh --update
    Update existing installation to latest version

  ./install.sh --list
    Show available skills and roles

INSTALL LOCATION:
  $INSTALL_DIR

For more information, see: https://github.com/dtsong/data-engineering-skills
EOF
}

list_available() {
  echo ""
  echo -e "${BLUE}Available Skills:${NC}"
  echo ""
  for skill in "${AVAILABLE_SKILLS[@]}"; do
    echo "  - $skill"
  done
  echo ""
  echo -e "${YELLOW}Planned Skills (not yet available):${NC}"
  echo ""
  for skill in "${ALL_SKILLS[@]}"; do
    if [[ ! " ${AVAILABLE_SKILLS[@]} " =~ " ${skill} " ]]; then
      echo "  - $skill"
    fi
  done
  echo ""
  echo -e "${BLUE}Available Roles:${NC}"
  echo ""
  for role in "${!ROLE_SKILLS[@]}"; do
    echo "  - $role: ${ROLE_SKILLS[$role]}"
  done
  echo ""
}

# Parse arguments
MODE="all"
SELECTED_SKILLS=()
UPDATE_MODE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --help)
      show_help
      exit 0
      ;;
    --list)
      list_available
      exit 0
      ;;
    --role)
      if [[ -z "${2:-}" ]]; then
        error "Missing role name. Use --list to see available roles."
      fi
      if [[ -z "${ROLE_SKILLS[$2]:-}" ]]; then
        error "Unknown role: $2. Use --list to see available roles."
      fi
      MODE="role"
      IFS=',' read -ra SELECTED_SKILLS <<< "${ROLE_SKILLS[$2]}"
      shift 2
      ;;
    --skills)
      if [[ -z "${2:-}" ]]; then
        error "Missing skills list. Use --list to see available skills."
      fi
      MODE="skills"
      IFS=',' read -ra SELECTED_SKILLS <<< "$2"
      shift 2
      ;;
    --update)
      UPDATE_MODE=true
      shift
      ;;
    *)
      error "Unknown option: $1. Use --help for usage."
      ;;
  esac
done

# Validate selected skills
if [[ "$MODE" == "skills" || "$MODE" == "role" ]]; then
  for skill in "${SELECTED_SKILLS[@]}"; do
    if [[ ! " ${AVAILABLE_SKILLS[@]} " =~ " ${skill} " ]]; then
      if [[ " ${ALL_SKILLS[@]} " =~ " ${skill} " ]]; then
        warn "Skill '$skill' is planned but not yet available. Skipping."
      else
        error "Unknown skill: $skill. Use --list to see available skills."
      fi
    fi
  done
  # Filter out unavailable skills
  FILTERED_SKILLS=()
  for skill in "${SELECTED_SKILLS[@]}"; do
    if [[ " ${AVAILABLE_SKILLS[@]} " =~ " ${skill} " ]]; then
      FILTERED_SKILLS+=("$skill")
    fi
  done
  SELECTED_SKILLS=("${FILTERED_SKILLS[@]}")

  if [[ ${#SELECTED_SKILLS[@]} -eq 0 ]]; then
    error "No available skills to install."
  fi
fi

# Update mode
if [[ "$UPDATE_MODE" == true ]]; then
  if [[ ! -d "$INSTALL_DIR" ]]; then
    error "Installation not found at $INSTALL_DIR. Use ./install.sh to install first."
  fi
  info "Updating installation at $INSTALL_DIR..."
  cd "$INSTALL_DIR"
  git pull
  success "Installation updated to latest version."
  echo ""
  info "Skills will auto-activate when relevant keywords are detected."
  exit 0
fi

# Check if already installed
if [[ -d "$INSTALL_DIR" ]]; then
  warn "Installation already exists at $INSTALL_DIR"
  read -p "Overwrite existing installation? (y/N): " -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    info "Installation cancelled. Use --update to update existing installation."
    exit 0
  fi
  info "Removing existing installation..."
  rm -rf "$INSTALL_DIR"
fi

# Create install directory
info "Creating installation directory..."
mkdir -p "$INSTALL_DIR"

# Install logic
if [[ "$MODE" == "all" ]]; then
  # Install all available skills
  info "Installing all available skills to $INSTALL_DIR..."

  # If running from repo directory, copy files
  if [[ -f "$SCRIPT_DIR/CATALOG.md" ]]; then
    info "Installing from local repository..."
    cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
  else
    # Clone from GitHub
    info "Cloning from $REPO_URL..."
    git clone "$REPO_URL" "$INSTALL_DIR"
  fi

  success "Installed all available skills:"
  for skill in "${AVAILABLE_SKILLS[@]}"; do
    echo "  - $skill"
  done

else
  # Install specific skills
  info "Installing selected skills..."

  # Create directory structure
  mkdir -p "$INSTALL_DIR/shared-references/data-engineering"

  # Copy selected skills
  for skill in "${SELECTED_SKILLS[@]}"; do
    if [[ -d "$SCRIPT_DIR/$skill" ]]; then
      info "Copying $skill..."
      cp -r "$SCRIPT_DIR/$skill" "$INSTALL_DIR/"
    else
      # Clone from GitHub and copy skill
      info "Downloading $skill from $REPO_URL..."
      TEMP_DIR=$(mktemp -d)
      git clone --depth 1 --filter=blob:none --sparse "$REPO_URL" "$TEMP_DIR"
      cd "$TEMP_DIR"
      git sparse-checkout set "$skill"
      cp -r "$skill" "$INSTALL_DIR/"
      cd -
      rm -rf "$TEMP_DIR"
    fi
  done

  # Copy shared references
  if [[ -d "$SCRIPT_DIR/shared-references" ]]; then
    info "Copying shared references..."
    cp -r "$SCRIPT_DIR/shared-references"/* "$INSTALL_DIR/shared-references/"
  else
    info "Downloading shared references..."
    TEMP_DIR=$(mktemp -d)
    git clone --depth 1 --filter=blob:none --sparse "$REPO_URL" "$TEMP_DIR"
    cd "$TEMP_DIR"
    git sparse-checkout set "shared-references"
    cp -r shared-references/* "$INSTALL_DIR/shared-references/"
    cd -
    rm -rf "$TEMP_DIR"
  fi

  # Copy catalog and README
  for file in CATALOG.md README.md LICENSE; do
    if [[ -f "$SCRIPT_DIR/$file" ]]; then
      cp "$SCRIPT_DIR/$file" "$INSTALL_DIR/"
    else
      # Download from GitHub
      curl -sSL "https://raw.githubusercontent.com/dtsong/data-engineering-skills/main/$file" -o "$INSTALL_DIR/$file" 2>/dev/null || true
    fi
  done

  success "Installed skills:"
  for skill in "${SELECTED_SKILLS[@]}"; do
    echo "  - $skill"
  done
fi

# Summary
echo ""
success "Installation complete!"
echo ""
info "Installation location: $INSTALL_DIR"
echo ""
info "Skills will auto-activate when Claude detects relevant keywords:"
echo "  - dbt-skill: dbt, models, tests, incremental, materialization"
echo "  - integration-patterns-skill: Fivetran, Airbyte, API, connector, CDC"
echo "  - streaming-data-skill: Kafka, Flink, stream, real-time, event"
echo "  - data-orchestration-skill: Dagster, Airflow, Prefect, DAG, schedule, orchestrate"
echo ""
info "Next steps:"
echo "  1. Start a new conversation in Claude Code"
echo "  2. Mention a keyword (e.g., 'Help me write a dbt model')"
echo "  3. The relevant skill will auto-activate"
echo ""
info "For more information, see:"
echo "  - Catalog: $INSTALL_DIR/CATALOG.md"
echo "  - README: $INSTALL_DIR/README.md"
echo "  - GitHub: $REPO_URL"
echo ""
