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
            echo "PermitFlow dev shell."
            echo "  python : $(python --version)"
            echo "  node   : $(node --version)"
            echo ""
            echo "Run modes:"
            echo "  nix run                  # local stack (assumes Ollama on this box)"
            echo "  nix run .#deploy-tunnel  # backend+frontend here, Ollama tunneled from GX10"
            echo "  nix run .#backend"
            echo "  nix run .#frontend"
            echo ""
          '';
        };

        # `nix run` (default) — run the whole stack on THIS machine.
        # Assumes Ollama is reachable at http://localhost:11434 (i.e. you are
        # on the GX10 itself). Use .#deploy-tunnel on the laptop instead.
        apps.default = self.apps.${system}.local;
        apps.local = {
          type = "app";
          program = toString (pkgs.writeShellScript "permitflow-local" ''
            set -uo pipefail
            export PATH="${pythonEnv}/bin:${pkgs.nodejs_22}/bin:$PATH"
            cd "''${PWD}"
            exec bash scripts/gx10-up.sh
          '');
        };

        # `nix run .#deploy-tunnel` — laptop dev mode: backend + frontend run
        # here, Ollama is brought to localhost via SSH tunnel to the GX10.
        apps.deploy-tunnel = {
          type = "app";
          program = toString (pkgs.writeShellScript "permitflow-deploy-tunnel" ''
            set -uo pipefail
            export PATH="${pkgs.nodejs_22}/bin:${pkgs.openssh}/bin:${pkgs.iproute2}/bin:$PATH"

            GX10="''${PERMITFLOW_GX10:-gx10-4896}"
            pids=()

            cleanup() {
              echo ""
              echo "[deploy-tunnel] shutting down…"
              for pid in "''${pids[@]}"; do
                kill "$pid" 2>/dev/null || true
              done
              pkill -f 'ssh.*-fN.*-L 11434:localhost:11434' 2>/dev/null || true
            }
            trap cleanup EXIT INT TERM

            if ss -tln 2>/dev/null | grep -q ':11434 '; then
              echo "[deploy-tunnel] Ollama tunnel already up on :11434"
            else
              echo "[deploy-tunnel] opening Ollama tunnel to $GX10…"
              ssh -fN -L 11434:localhost:11434 "$GX10" || {
                echo "[deploy-tunnel] tunnel failed — Ollama-backed endpoints will 500"
              }
            fi

            cd "''${PWD}"

            if [ ! -d frontend/node_modules ]; then
              echo "[deploy-tunnel] installing frontend deps…"
              ( cd frontend && npm install )
            fi

            echo "[deploy-tunnel] starting backend on :8000…"
            ( cd backend && exec ${pythonEnv}/bin/uvicorn main:app --reload --port 8000 ) &
            pids+=($!)

            echo "[deploy-tunnel] starting frontend on :5173…"
            ( cd frontend && exec npm run dev ) &
            pids+=($!)

            echo ""
            echo "[deploy-tunnel] ready:"
            echo "  backend  → http://localhost:8000"
            echo "  frontend → http://localhost:5173"
            echo "  ollama   → http://localhost:11434  (tunneled to $GX10)"
            echo ""
            echo "[deploy-tunnel] Ctrl-C to stop everything"
            wait
          '');
        };

        # `nix run .#backend`
        apps.backend = {
          type = "app";
          program = toString (pkgs.writeShellScript "permitflow-backend" ''
            cd "''${PWD}/backend"
            exec ${pythonEnv}/bin/uvicorn main:app --reload --port 8000
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
