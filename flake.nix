{
  description = "PermitFlow — Toronto permit consolidation, NVIDIA hackathon";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        pythonEnv = pkgs.python313.withPackages (ps: with ps; [
          fastapi
          uvicorn
          pandas
          scikit-learn
          numpy
          duckdb
          requests
          python-multipart
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            pythonEnv
            pkgs.nodejs_22
            pkgs.curl
            pkgs.jq
          ];

          shellHook = ''
            echo ""
            echo "PermitFlow dev shell ready."
            echo "  python : $(python --version)"
            echo "  node   : $(node --version)"
            echo ""
            echo "Quick start:"
            echo "  1. Tunnel Ollama:  ssh -fN -L 11434:localhost:11434 gx10-4896"
            echo "  2. Backend:        cd backend && uvicorn main:app --reload --port 8000"
            echo "  3. Frontend:       cd frontend && npm install && npm run dev"
            echo ""
          '';
        };

        # `nix run .#backend`
        apps.backend = {
          type = "app";
          program = toString (pkgs.writeShellScript "permitflow-backend" ''
            cd "''${PWD}/backend"
            exec ${pythonEnv}/bin/uvicorn main:app --reload --port 8000
          '');
        };

        # `nix run` (default) — backend + frontend + Ollama tunnel
        apps.default = self.apps.${system}.dev;
        apps.dev = {
          type = "app";
          program = toString (pkgs.writeShellScript "permitflow-dev" ''
            set -uo pipefail
            export PATH="${pkgs.nodejs_22}/bin:${pkgs.openssh}/bin:${pkgs.iproute2}/bin:$PATH"

            GX10="''${PERMITFLOW_GX10:-gx10-4896}"
            pids=()

            cleanup() {
              echo ""
              echo "[dev] shutting down…"
              for pid in "''${pids[@]}"; do
                kill "$pid" 2>/dev/null || true
              done
              pkill -f 'ssh.*-fN.*-L 11434:localhost:11434' 2>/dev/null || true
            }
            trap cleanup EXIT INT TERM

            if ss -tln 2>/dev/null | grep -q ':11434 '; then
              echo "[dev] Ollama tunnel already up on :11434"
            else
              echo "[dev] opening Ollama tunnel to $GX10…"
              ssh -fN -L 11434:localhost:11434 "$GX10" || {
                echo "[dev] tunnel failed — Ollama-backed endpoints will 500 until you fix it"
              }
            fi

            cd "''${PWD}"

            if [ ! -d frontend/node_modules ]; then
              echo "[dev] installing frontend deps…"
              ( cd frontend && npm install )
            fi

            echo "[dev] starting backend on :8000…"
            ( cd backend && exec ${pythonEnv}/bin/uvicorn main:app --reload --port 8000 ) &
            pids+=($!)

            echo "[dev] starting frontend on :5173…"
            ( cd frontend && exec npm run dev ) &
            pids+=($!)

            echo ""
            echo "[dev] ready:"
            echo "  backend  → http://localhost:8000"
            echo "  frontend → http://localhost:5173"
            echo "  ollama   → http://localhost:11434  (tunneled to $GX10)"
            echo ""
            echo "[dev] Ctrl-C to stop everything"
            wait
          '');
        };

        # `nix run .#gx10` — start the full stack on the GX10 using whatever
        # version is currently checked out there. Update is a manual `ssh
        # gx10 'cd ~/permitflow/code && git pull'` when you want to refresh.
        apps.gx10 = {
          type = "app";
          program = toString (pkgs.writeShellScript "permitflow-gx10" ''
            set -uo pipefail
            export PATH="${pkgs.openssh}/bin:$PATH"

            GX10="''${PERMITFLOW_GX10:-gx10-4896}"
            REMOTE="''${PERMITFLOW_REMOTE_PATH:-~/permitflow/code}"

            echo "[gx10] starting stack on $GX10 (uses whatever's at $REMOTE)…"
            echo "[gx10] to update: ssh $GX10 'cd $REMOTE && git pull'"
            echo ""
            exec ssh -tt "$GX10" "bash $REMOTE/scripts/gx10-up.sh"
          '');
        };

        # `nix run .#frontend`
        apps.frontend = {
          type = "app";
          program = toString (pkgs.writeShellScript "permitflow-frontend" ''
            export PATH="${pkgs.nodejs_22}/bin:$PATH"
            cd "''${PWD}/frontend"
            if [ ! -d node_modules ]; then
              npm install
            fi
            exec npm run dev
          '');
        };
      }
    );
}
