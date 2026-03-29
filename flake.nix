{
  description = "Standalone flake packaging Bitwarden Secrets Manager CLI (bws)";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      lib = nixpkgs.lib;
      systems = [
        "aarch64-darwin"
        "x86_64-darwin"
        "aarch64-linux"
        "x86_64-linux"
      ];
      forAllSystems = lib.genAttrs systems;
    in
    {
      overlays.default = final: prev: {
        bws = final.callPackage ./pkgs/bws/package.nix { };
      };

      devShells = forAllSystems (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              gh
              git
              nix-update
              python3
            ];
          };
        }
      );

      packages = forAllSystems (
        system:
        let
          pkgs = import nixpkgs {
            inherit system;
            config.allowUnfreePredicate =
              pkg: builtins.elem (lib.getName pkg) [ "bws" ];
            overlays = [ self.overlays.default ];
          };
        in
        {
          inherit (pkgs) bws;
          default = pkgs.bws;
        }
      );
    };
}
