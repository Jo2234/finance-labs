"""Build all ten distributions and exercise installed wheels with README examples.

Run with Python 3.11+ and `build`, `setuptools>=77`, `wheel`, and `pytest` installed.
The output directory must be empty. Package build dependencies may use the network;
the lab tests, installed CLI examples, and wheel installation run offline.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import venv
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=ROOT, env=None):
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{' '.join(map(str, args))}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "release")
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        parser.error(f"Output directory must be empty: {out}")
    labs = sorted(ROOT.glob("labs/*/pyproject.toml"))
    if len(labs) != 10:
        raise RuntimeError("Update release coverage when the collection changes")
    evidence = {"python": sys.version.split()[0], "labs": []}
    for path in labs:
        lab = path.parent
        project = tomllib.loads(path.read_text())["project"]
        test_log = run(sys.executable, "-m", "pytest", "-q", cwd=lab,
                       env=dict(os.environ, PYTHONPATH=str(lab / "src")))
        run(sys.executable, "-m", "build", "--outdir", str(out), str(lab))
        evidence["labs"].append({"lab": lab.name, "package": project["name"],
                                 "version": project["version"], "tests": test_log.strip()})
        print(f"Built and tested {lab.name}", flush=True)
    wheels = sorted(out.glob("*.whl"))
    sdists = sorted(out.glob("*.tar.gz"))
    if len(wheels) != len(labs) or len(sdists) != len(labs):
        raise RuntimeError("Expected one wheel and one source distribution per lab")
    for wheel in wheels:
        with zipfile.ZipFile(wheel) as archive:
            license_paths = [p for p in archive.namelist() if p.endswith("/licenses/LICENSE")]
            if len(license_paths) != 1 or archive.read(license_paths[0]) != (ROOT / "LICENSE").read_bytes():
                raise RuntimeError(f"Missing or incorrect license: {wheel.name}")
    for sdist in sdists:
        with tarfile.open(sdist) as archive:
            if not any("/examples/" in p or "/data/" in p for p in archive.getnames()):
                raise RuntimeError(f"Missing example inputs: {sdist.name}")
    commands = [line.split("`", 2)[1] for line in (ROOT / "README.md").read_text().splitlines()
                if line.startswith("| [") and "`PYTHONPATH=" in line]
    if len(commands) != len(labs):
        raise RuntimeError("Expected one README example per lab")
    with tempfile.TemporaryDirectory(prefix="finance-labs-release-") as temporary:
        environment = Path(temporary) / "venv"
        venv.create(environment, with_pip=True)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        clean_env = {key: value for key, value in os.environ.items()
                     if key not in ("PYTHONPATH", "PYTHONHOME")}
        run(str(python), "-m", "pip", "install", "--no-index", "--no-deps",
            *(str(wheel) for wheel in wheels), env=clean_env)
        evidence["examples"] = []
        for command in commands:
            args = shlex.split(command)
            # Drop the checkout PYTHONPATH and python3 prefix: use installed wheels.
            output = run(str(python), *args[2:], env=clean_env)
            if not output.strip():
                raise RuntimeError(f"Empty example output: {command}")
            evidence["examples"].append({"command": command, "installed_wheel_output": output})
    (out / "validation.json").write_text(json.dumps(evidence, indent=2) + "\n")
    checksums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
                 for p in sorted(out.iterdir()) if p.is_file()]
    (out / "SHA256SUMS").write_text("".join(checksums))
    print(f"Verified {len(wheels)} wheels, {len(sdists)} source distributions and {len(commands)} installed CLI examples.")


if __name__ == "__main__":
    main()
