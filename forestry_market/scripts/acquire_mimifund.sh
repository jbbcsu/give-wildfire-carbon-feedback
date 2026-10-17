#!/bin/sh
set -eu

tag="v3.13.0"
commit="3f5fe29ffb753a49ff070d04b74ae42abd23576b"
root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
dest="$root/data/raw/MimiFUND-$tag"

mkdir -p "$root/data/raw"
if [ ! -d "$dest/.git" ]; then
  git clone --branch "$tag" --depth 1 https://github.com/fund-model/MimiFUND.jl.git "$dest"
fi

actual="$(git -C "$dest" rev-parse HEAD)"
if [ "$actual" != "$commit" ]; then
  echo "ERROR: expected $commit but found $actual" >&2
  exit 1
fi

echo "$dest"
