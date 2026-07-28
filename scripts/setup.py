#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────────────────────────
# ogclews-link setup (Windows / macOS / Linux) — the cross-platform installer.
#
# Stands up the link's OWN isolated environment and makes `ogclews-link` runnable.
# The link is deliberately ogcore-free: it never imports ogcore — to solve, it
# SUBPROCESSES an OG model's own interpreter. So this installer:
#   (1) creates the link's uv venv (numpy/pandas/scipy/openpyxl/matplotlib only),
#   (2) verifies the `ogclews-link` CLI,
#   (3) registers an OG country model — installed in ITS OWN env, either an existing
#       checkout or fetched here (git clone + uv sync) — so
#       `ogclews-link run coupled` has a model to drive.
#
# Runs under any Python >= 3.8 (stdlib only). POSIX users can keep calling
# ./scripts/setup.sh; Windows users: python scripts\setup.py (or scripts\setup.ps1).
#
# Usage:
#   python scripts/setup.py                     create the link venv + verify the CLI
#   python scripts/setup.py --check             verify an existing install only (no changes)
#   python scripts/setup.py --dev               also install the dev extra (pytest) + run the tests
#                                               (use --dev on a dev checkout: plain `uv sync` removes extras)
#   python scripts/setup.py --og-path <dir>     register an already-installed OG model checkout
#        [--key <k>]                            registry key (default: dir basename; use for worktrees, e.g. og-phl)
#   python scripts/setup.py --install-og <key>  STANDALONE convenience (no MUIOGO): fetch+install an OG country
#                                               model (git clone + uv sync), then register it. Under MUIOGO,
#                                               install OG models via its OG tab instead (the link then finds
#                                               them automatically). keys: og-phl|og-eth|og-zaf|og-idn
#        [--og-dest <dir>]                      where to install it (default: the link repo's parent)
#
# Respects $OGCLEWS_MODEL_REGISTRY (registry file location; default ./og_model_registry.json).
# ──────────────────────────────────────────────────────────────────────────────
import argparse
import os
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
IS_WINDOWS = os.name == "nt"

# OG country models the standalone convenience can fetch (mirrors OG-Core/scripts/install.sh's
# uv-migrated catalog; the upstream installer itself is bash-only, so the clone+sync is inline here).
OG_CATALOG = {
    "og-phl": ("EAPD-DRB", "OG-PHL"),
    "og-eth": ("EAPD-DRB", "OG-ETH"),
    "og-zaf": ("EAPD-DRB", "OG-ZAF"),
    "og-idn": ("EAPD-DRB", "OG-IDN"),
}

# ---- pretty output (plain when not a tty; Windows 10+ consoles speak ANSI once VT is nudged on) ----
if sys.stdout.isatty():
    if IS_WINDOWS:
        os.system("")  # enables ANSI escape processing in cmd/PowerShell consoles
    B, G, Y, R, N = "\033[1m", "\033[32m", "\033[33m", "\033[31m", "\033[0m"
else:
    B = G = Y = R = N = ""


def info(msg):
    print("%s==>%s %s" % (B, N, msg))


def ok(msg):
    print("%s  ok%s %s" % (G, N, msg))


def warn(msg):
    print("%s  ! %s %s" % (Y, N, msg))


def die(msg):
    print("%s  x %s %s" % (R, N, msg), file=sys.stderr)
    sys.exit(1)


def run(cmd, **kw):
    """subprocess.run with loud failure; cwd defaults to the project root."""
    kw.setdefault("cwd", PROJECT_ROOT)
    return subprocess.run(cmd, **kw)


# ---- uv resolution / bootstrap -----------------------------------------------------


def _uv_candidates():
    home = os.path.expanduser("~")
    exe = "uv.exe" if IS_WINDOWS else "uv"
    return [
        os.path.join(home, ".local", "bin", exe),
        os.path.join(home, ".cargo", "bin", exe),
    ]


def find_uv():
    """Absolute path to uv, probing the installer's default dirs too (a just-installed uv
    is not on this process's PATH)."""
    hit = shutil.which("uv")
    if hit:
        return hit
    for cand in _uv_candidates():
        if os.path.isfile(cand):
            return cand
    return None


def ensure_uv():
    uv = find_uv()
    if uv:
        return uv
    info("uv not found — installing it (https://astral.sh/uv)")
    if IS_WINDOWS:
        r = run(["powershell", "-NoProfile", "-ExecutionPolicy", "ByPass", "-Command",
                 "irm https://astral.sh/uv/install.ps1 | iex"])
    else:
        r = run(["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"])
    uv = find_uv() if r.returncode == 0 else None
    if not uv:
        die("uv install failed; install it manually, then re-run (https://docs.astral.sh/uv/)")
    return uv


# ---- verification ------------------------------------------------------------------


def verify_cli(uv):
    info("Verifying the ogclews-link CLI")
    for probe in (["models", "list"], ["--help"]):
        if run([uv, "run", "ogclews-link"] + probe,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            ok("CLI runs")
            return
    die("the 'ogclews-link' CLI did not run — see 'uv run ogclews-link --help'")


def have_registered_model(uv):
    r = run([uv, "run", "ogclews-link", "models", "list"],
            capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode == 0 and ("couplable" in out.lower() or "[x]" in out)


def model_interpreter(og_path):
    """The OG checkout's venv interpreter, probing both layouts (same idiom as
    ogclews_link.registry.venv_python — not importable here: setup runs OUTSIDE the venv)."""
    for parts in (("Scripts", "python.exe"), ("bin", "python")):
        cand = os.path.join(og_path, ".venv", *parts)
        if os.path.isfile(cand):
            return cand
    return None


# ---- main --------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(
        prog="setup.py", description="ogclews-link installer (Windows / macOS / Linux)")
    ap.add_argument("--check", action="store_true", help="verify an existing install only (no changes)")
    ap.add_argument("--dev", action="store_true", help="also install the dev extra (pytest) + run the tests")
    ap.add_argument("--og-path", metavar="DIR", help="register an already-installed OG model checkout")
    ap.add_argument("--key", metavar="K", help="registry key (default: dir basename)")
    ap.add_argument("--install-og", metavar="KEY", choices=sorted(OG_CATALOG),
                    help="fetch+install an OG country model (git clone + uv sync), then register it")
    ap.add_argument("--og-dest", metavar="DIR", help="where --install-og puts the model (default: repo parent)")
    a = ap.parse_args()

    # a dir whose basename isn't the expected repo key (e.g. a worktree) needs --key so
    # `run coupled` can look the country up (country og_repo -> registry key, e.g. og-phl)
    if a.install_og and not a.key:
        a.key = a.install_og
    og_dest = os.path.abspath(a.og_dest) if a.og_dest else os.path.dirname(PROJECT_ROOT)

    # ---- guard: an active conda env breaks uv's venv resolution ----
    if os.environ.get("CONDA_DEFAULT_ENV"):
        die("Conda env '%s' is active. Run 'conda deactivate' (until no env shows), then re-run."
            % os.environ["CONDA_DEFAULT_ENV"])

    # ---- --check: verify an existing install, change nothing ----
    if a.check:
        uv = find_uv() or die("uv not found (run without --check to install it)")
        if not os.path.isdir(os.path.join(PROJECT_ROOT, ".venv")):
            die("no .venv here (run without --check to create it)")
        verify_cli(uv)
        info("Registered OG models:")
        run([uv, "run", "ogclews-link", "models", "list"])
        return

    # ---- 1. the link's own environment ----
    uv = ensure_uv()
    info("Creating the link's isolated venv (uv sync)")
    sync = [uv, "sync"] + (["--extra", "dev"] if a.dev else [])
    if run(sync).returncode != 0:
        die("uv sync failed")
    ok("link venv ready at %s (ogcore-free)" % os.path.join(PROJECT_ROOT, ".venv"))

    # ---- 2. verify (+ tests in --dev) ----
    verify_cli(uv)
    if a.dev:
        info("Running the test suite")
        if run([uv, "run", "pytest", "tests/", "-q"]).returncode != 0:
            die("test suite failed")

    # ---- 3. OG country model: optional install, then register ----
    og_path = a.og_path
    if a.install_og:
        owner, repo = OG_CATALOG[a.install_og]
        og_path = os.path.join(og_dest, repo)
        if not os.path.isdir(og_path):
            info("Cloning %s/%s into %s" % (owner, repo, og_dest))
            if run(["git", "clone", "https://github.com/%s/%s.git" % (owner, repo), og_path],
                   cwd=og_dest).returncode != 0:
                die("git clone failed (https://github.com/%s/%s)" % (owner, repo))
        info("Installing %s's own env (uv sync — can take a minute)" % repo)
        if run([uv, "sync"], cwd=og_path).returncode != 0:
            die("uv sync failed in %s" % og_path)

    if og_path:
        og_path = os.path.abspath(og_path)
        if not model_interpreter(og_path):
            die("no interpreter at %s — build the OG model first (its own 'uv sync'), or use --install-og"
                % os.path.join(og_path, ".venv", "Scripts|bin", "python"))
        info("Registering the OG model at %s" % og_path)
        reg = [uv, "run", "ogclews-link", "models", "register", "--path", og_path]
        if a.key:
            reg += ["--key", a.key]
        if run(reg).returncode != 0:
            die("model registration failed")
        ok("registered")
    elif not have_registered_model(uv):
        warn("No OG model is registered yet. 'run coupled' needs one — re-run with either:")
        warn("    python scripts/setup.py --install-og og-phl       # fetch + register a country model")
        warn("    python scripts/setup.py --og-path <OG-checkout>   # register one you already installed")

    # ---- summary ----
    print()
    info("Registered OG models:")
    run([uv, "run", "ogclews-link", "models", "list"])
    print()
    ok("ogclews-link is installed.")
    setenv = "set" if IS_WINDOWS else "export"
    print("""Next — point at your CLEWS scenarios (from a MUIOGO install) and run:
  {0} OGCLEWS_MUIOGO_HOME=<path to MUIOGO>          # or place MUIOGO at ../MUIOGO
  {0} OGCLEWS_CLEWS_CASE=Philippines_v9
  {0} OGCLEWS_CLEWS_BASE_RUN=Base_v9
  {0} OGCLEWS_CLEWS_REFORM_RUN=PEP_v9
  uv run ogclews-link run coupled --out ./ogclews_runs   # (or pass --clews-base/--clews-reform)""".format(setenv))


if __name__ == "__main__":
    main()
