"""Shallow-clone mathlib4 into data/mathlib4 (no-op if already present)."""

import subprocess

import config


def main():
    if (config.MATHLIB_DIR / ".git").exists():
        print(f"{config.MATHLIB_DIR} already exists, skipping clone.")
        return
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", config.MATHLIB_REPO, str(config.MATHLIB_DIR)],
        check=True,
    )


if __name__ == "__main__":
    main()
