# `bws-flake`

Standalone flake packaging the Bitwarden Secrets Manager CLI (`bws`) from source.

Current packaged version: `2.0.0`

## Use as a package

```bash
nix profile install github:SecBear/bws-flake
```

## Use as an overlay

```nix
{
  inputs.bws-flake.url = "github:SecBear/bws-flake";

  outputs = { self, nixpkgs, bws-flake, ... }: {
    nixosConfigurations.example = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        ({ pkgs, ... }: {
          nixpkgs.overlays = [ bws-flake.overlays.default ];
          environment.systemPackages = [ pkgs.bws ];
        })
      ];
    };
  };
}
```

## Build

```bash
nix build .#bws
```
