{
  description = "orbitr — academic literature search CLI";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    nixpkgs,
    flake-utils,
    ...
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = import nixpkgs {inherit system;};

      pythonPackages = with pkgs; [
        python312
        uv
      ];

      devTools = with pkgs; [
        ruff
        pyright
        git
      ];

      allPackages = pythonPackages ++ devTools;
    in {
      devShell = pkgs.mkShell {
        buildInputs = allPackages;

        shellHook = ''
          echo "orbitr dev environment loaded"
          echo "Python: $(python --version)"
          echo "uv:     $(uv --version)"
          echo ""
          echo "Setup:  uv sync && uv tool install --editable ."
          echo "Test:   uv run pytest"
          echo "Lint:   ruff check src/ tests/"
        '';
      };
    });
}
