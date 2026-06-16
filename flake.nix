{
  description = "Python Dev Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          # Системные зависимости (компиляторы, C-библиотеки)
          buildInputs = with pkgs; [
            python314
            uv           # Сверхбыстрый менеджер пакетов и venv
            gcc          # Нужен для компиляции C-extensions
            zlib         # Пример системной либы
            libffi
            pkg-config
          ];

          # Хак для NixOS: чтобы Python-пакеты с C-расширениями находили системные .so файлы
          shellHook = ''
            export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath [
              pkgs.zlib
              pkgs.libffi
              pkgs.stdenv.cc.cc.lib
            ]}:$LD_LIBRARY_PATH
            echo "🐍 Python Nix-Shell Activated!"
          '';
        };
      });
}