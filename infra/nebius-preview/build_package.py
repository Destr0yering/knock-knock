"""Build the hosted preview zip from preinstalled Linux ARM dependencies."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--asm-exec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    pkg = args.package_dir.resolve()
    if not pkg.is_dir() or not args.asm_exec.is_file():
        parser.error("Install dependencies into --package-dir and provide an asm-exec file")
    if args.output.resolve().is_relative_to(pkg):
        parser.error("The output zip must be outside the package directory")
    mappings = [
        ("src/knock_knock", "knock_knock"),
        ("fixtures/manifests/group-arrival.json", "fixtures/manifests/group-arrival.json"),
        ("scripts/nebius_review_demo.py", "scripts/nebius_review_demo.py"),
        ("scripts/nebius_review_demo.html", "scripts/nebius_review_demo.html"),
        ("infra/nebius-preview/handler.py", "handler.py"),
        ("infra/nebius-preview/index.html", "index.html"),
    ]
    for source, destination in mappings:
        src, dst = root / source, pkg / destination
        if src.is_dir():
            shutil.copytree(
                src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
            )
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    shutil.copy2(args.asm_exec, pkg / "asm-exec")
    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in pkg.rglob("*"):
            if (
                path.is_file()
                and "__pycache__" not in path.parts
                and path.suffix not in {".pyc", ".exe", ".dll"}
            ):
                archive.write(path, path.relative_to(pkg).as_posix())
    print(f"Package: {args.output} ({args.output.stat().st_size} bytes)")
    print(f"SHA-256: {hashlib.sha256(args.output.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
