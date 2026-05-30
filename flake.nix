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
            cd ${toString ./.}/backend
            exec ${pythonEnv}/bin/uvicorn main:app --reload --port 8000
          '');
        };

        # `nix run .#frontend`
        apps.frontend = {
          type = "app";
          program = toString (pkgs.writeShellScript "permitflow-frontend" ''
            cd ${toString ./.}/frontend
            if [ ! -d node_modules ]; then
              ${pkgs.nodejs_22}/bin/npm install
            fi
            exec ${pkgs.nodejs_22}/bin/npm run dev
          '');
        };
      }
    );
}
