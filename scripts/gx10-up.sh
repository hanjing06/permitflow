#!/usr/bin/env bash
#
# Start backend + frontend on the GX10, both bound on 0.0.0.0 so the laptop
# browser can reach them.  Invoked remotely by `nix run .#gx10` after rsync.
# Can also be run directly from the GX10 once the repo is synced.
#
set -uo pipefail

cd "$(dirname "$0")/.."
ROOT="$PWD"
HOST="${PERMITFLOW_HOSTNAME:-gx10-4896}"

pids=()
cleanup() {
  echo ""
  echo "[gx10] shutting down…"
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

# --- backend python deps --------------------------------------------------
# If we're under `nix run`, the python env (with fastapi/uvicorn/numpy/etc.)
# is already on PATH. Use it directly — pip-installing numpy into a venv
# against a Nix Python fails at runtime (missing libstdc++.so.6).
# Only create a venv if the deps aren't already importable.
if python3 -c 'import fastapi, uvicorn, pandas, numpy, sklearn, requests' 2>/dev/null; then
  echo "[gx10] python deps already available (using $(command -v python3))"
  UVICORN="$(command -v uvicorn)"
else
  if [ ! -d backend/.venv ]; then
    echo "[gx10] creating backend venv + installing deps…"
    python3 -m venv backend/.venv
    ./backend/.venv/bin/pip install --quiet --upgrade pip
    ./backend/.venv/bin/pip install --quiet -r requirements.txt
  fi
  UVICORN="$ROOT/backend/.venv/bin/uvicorn"
fi

# --- frontend deps --------------------------------------------------------
if [ ! -d frontend/node_modules ]; then
  echo "[gx10] npm install…"
  ( cd frontend && npm install --silent )
fi

# --- kill any leftover processes on our ports ----------------------------
for port in 8000 5173; do
  pid=$(ss -tlnp 2>/dev/null | awk -v p=":$port " '$0 ~ p {print}' | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2)
  if [ -n "$pid" ]; then
    echo "[gx10] killing leftover process on :$port (pid $pid)"
    kill "$pid" 2>/dev/null || true
    sleep 1
  fi
done

# --- start backend on :8000, LAN-bound -----------------------------------
echo "[gx10] backend  → http://$HOST:8000"
(
  cd "$ROOT/backend"
  exec "$UVICORN" main:app --host 0.0.0.0 --port 8000 --reload
) &
pids+=($!)

# --- start frontend on :5173, LAN-bound, pointed at GX10 backend ---------
echo "[gx10] frontend → http://$HOST:5173"
(
  cd "$ROOT/frontend"
  exec env VITE_API_URL="http://$HOST:8000" npm run dev -- --host 0.0.0.0
) &
pids+=($!)

echo ""
echo "[gx10] open in your laptop browser: http://$HOST:5173"
echo "[gx10] Ollama is already local on this box at :11434 — no tunnel needed"
echo "[gx10] Ctrl-C here to stop everything"
wait
