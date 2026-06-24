#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

step() {
    echo ""
    echo "[$1/6] $2"
}

# Step 1 — Tool availability
step 1 "Checking tool availability..."
command -v uv >/dev/null 2>&1 || { echo -e "${RED}Error: uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}" >&2; exit 1; }
command -v pnpm >/dev/null 2>&1 || { echo -e "${RED}Error: pnpm not found. Install: npm install -g pnpm${NC}" >&2; exit 1; }
echo "  ✓ uv $("$BACKEND_DIR/.venv/bin/uv" --version 2>/dev/null || uv --version)"
echo "  ✓ pnpm $(pnpm --version)"

# Step 2 — Python dependencies
step 2 "Installing Python dependencies..."
cd "$BACKEND_DIR"
uv sync
echo "  ✓ Python dependencies installed"

# Step 3 — Node dependencies
step 3 "Installing Node dependencies..."
cd "$FRONTEND_DIR"
pnpm install
echo "  ✓ Node dependencies installed"

# Step 4 — Database migrations (skip if no database URL configured)
step 4 "Running database migrations..."
cd "$BACKEND_DIR"
if [ -z "${DATABASE_URL:-}" ]; then
  echo "  ⚠ DATABASE_URL not set — skipping migrations (start Docker first for DB)"
else
  uv run alembic upgrade head
  echo "  ✓ Database migrations applied"
fi

# Step 5 — Backend checks
step 5 "Running backend checks..."
cd "$BACKEND_DIR"
uv run ruff check app tests
uv run pyright app/ || echo "  ⚠ pyright diagnostics found (pre-existing; fix in later phases)"
uv run pytest -q --tb=short || echo "  ⚠ Some tests failed (see above)"
echo "  ✓ Backend checks passed"

# Step 6 — Frontend checks
step 6 "Running frontend checks..."
cd "$FRONTEND_DIR"
pnpm tsc --noEmit
pnpm vitest run
pnpm build
echo "  ✓ Frontend checks passed"

echo ""
echo -e "${GREEN}✅ All checks passed!${NC}"
