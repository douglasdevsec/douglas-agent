"""Tests for the Douglas/Hermes environment + home-directory compatibility
chain implemented in hermes_bootstrap.py (normalize_douglas_env() and its
helpers). See douglas/README.md, section "Cadena canonica de resolucion
Douglas/Hermes", for the chain these tests verify.

Uses tmp_path + monkeypatch throughout. Never touches the real system home
or the real HERMES_HOME/DOUGLAS_HOME environment.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import hermes_bootstrap
import hermes_constants

_DOUGLAS_HERMES_VARS = [k for k in os.environ if k.startswith(("DOUGLAS_", "HERMES_"))]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Strip every DOUGLAS_*/HERMES_* var and LOCALAPPDATA before each test.

    normalize_douglas_env() derives everything from os.environ, so a leaked
    var from the real environment (or a previous test) would make these
    tests flaky depending on where they run.
    """
    for key in _DOUGLAS_HERMES_VARS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Point Path.home() at an empty tmp_path subdirectory for this test."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    return home


def _set_platform(monkeypatch, *, windows: bool) -> None:
    """Flip hermes_bootstrap's cached platform flag.

    hermes_bootstrap._IS_WINDOWS is computed once at import time from
    sys.platform, so patching sys.platform alone would not affect it —
    patch the module's own flag directly instead.
    """
    monkeypatch.setattr(hermes_bootstrap, "_IS_WINDOWS", windows)


# ── Env var priority: DOUGLAS_HOME / HERMES_HOME ────────────────────────────


def test_douglas_home_env_wins_over_everything(monkeypatch, fake_home):
    _set_platform(monkeypatch, windows=False)
    douglas_target = str(fake_home / "custom-douglas-target")
    hermes_target = str(fake_home / "custom-hermes-target")
    monkeypatch.setenv("DOUGLAS_HOME", douglas_target)
    monkeypatch.setenv("HERMES_HOME", hermes_target)
    # Both candidate directories exist on disk too — env still wins over disk.
    (fake_home / ".douglas").mkdir()
    (fake_home / ".hermes").mkdir()

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_HOME"] == douglas_target


def test_hermes_home_env_respected_when_douglas_unset(monkeypatch, fake_home):
    _set_platform(monkeypatch, windows=False)
    hermes_target = str(fake_home / "custom-hermes-target")
    monkeypatch.setenv("HERMES_HOME", hermes_target)

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_HOME"] == hermes_target


def test_both_set_douglas_wins(monkeypatch, fake_home):
    _set_platform(monkeypatch, windows=False)
    douglas_target = str(fake_home / "d")
    hermes_target = str(fake_home / "h")
    monkeypatch.setenv("DOUGLAS_HOME", douglas_target)
    monkeypatch.setenv("HERMES_HOME", hermes_target)

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_HOME"] == douglas_target
    assert os.environ["HERMES_HOME"] != hermes_target


def test_empty_douglas_home_does_not_override_hermes_home(monkeypatch, fake_home):
    """An empty-string DOUGLAS_HOME must be treated as unset, matching how
    hermes_constants treats HERMES_HOME=""."""
    _set_platform(monkeypatch, windows=False)
    hermes_target = str(fake_home / "h")
    monkeypatch.setenv("DOUGLAS_HOME", "")
    monkeypatch.setenv("HERMES_HOME", hermes_target)

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_HOME"] == hermes_target


# ── Fixed douglas-branded default, never a sibling hermes dir (POSIX) ───────
#
# A hermes-named directory is never adopted automatically, even if it
# exists — it may belong to a completely unrelated, foreign install of the
# upstream Hermes Agent product this app is forked from, and must never be
# treated as "my own data under the old name." See douglas/README.md,
# "Cadena canonica de resolucion Douglas/Hermes".


def test_legacy_douglas_dir_migrated_to_douglas_agent_posix(monkeypatch, fake_home):
    """A pre-2026-08-06 ~/.douglas install (this fork's own old default
    name, before ronda 4's rename) is migrated in place to ~/.douglas-agent
    — not left orphaned, and not merely ignored. See douglas/PROGRESS.md,
    ronda 4, and _migrate_legacy_home_dir_name()."""
    _set_platform(monkeypatch, windows=False)
    legacy = fake_home / ".douglas"
    legacy.mkdir()
    (legacy / "config.yaml").write_text("marker: real-user-data")

    hermes_bootstrap.normalize_douglas_env()

    new_home = fake_home / ".douglas-agent"
    assert os.environ["HERMES_HOME"] == str(new_home)
    assert not legacy.exists()
    assert (new_home / "config.yaml").read_text() == "marker: real-user-data"


def test_only_hermes_dir_exists_posix_is_not_adopted(monkeypatch, fake_home):
    """A sibling ~/.hermes (possibly a foreign, unrelated Hermes Agent
    install) must never be silently adopted — Douglas always defaults to
    its own directory, existing or not."""
    _set_platform(monkeypatch, windows=False)
    (fake_home / ".hermes").mkdir()

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_HOME"] == str(fake_home / ".douglas-agent")


def test_douglas_agent_dir_exists_posix_skips_migration(monkeypatch, fake_home):
    """Once ~/.douglas-agent already exists, migration is a no-op even if a
    stale ~/.douglas sits next to it (e.g. a second run, or a leftover from
    a partially-failed migration) — never silently merges/overwrites."""
    _set_platform(monkeypatch, windows=False)
    (fake_home / ".douglas-agent").mkdir()
    (fake_home / ".douglas").mkdir()

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_HOME"] == str(fake_home / ".douglas-agent")
    assert (fake_home / ".douglas").exists()


def test_neither_exists_defaults_to_douglas_agent_posix(monkeypatch, fake_home):
    """Fresh install: neither directory exists yet, default target is
    ~/.douglas-agent (the function does not create it — it only selects the
    path; Hermes creates HERMES_HOME lazily on first write, same as
    today)."""
    _set_platform(monkeypatch, windows=False)

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_HOME"] == str(fake_home / ".douglas-agent")
    assert not (fake_home / ".douglas-agent").exists()


# ── Fixed douglas-branded default, never a sibling hermes dir (Windows) ─────


def test_windows_legacy_douglas_appdata_migrated(monkeypatch, fake_home, tmp_path):
    """A pre-2026-08-06 %LOCALAPPDATA%\\douglas install (this fork's own
    old default name) is migrated in place to %LOCALAPPDATA%\\douglas-agent
    — never merely reused under its old name, and never confused with a
    sibling %LOCALAPPDATA%\\hermes, which is left untouched."""
    _set_platform(monkeypatch, windows=True)
    local_appdata = tmp_path / "AppData" / "Local"
    local_appdata.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))
    legacy = local_appdata / "douglas"
    legacy.mkdir()
    (local_appdata / "hermes").mkdir()

    hermes_bootstrap.normalize_douglas_env()

    new_home = local_appdata / "douglas-agent"
    assert os.environ["HERMES_HOME"] == str(new_home)
    assert not legacy.exists()
    assert (local_appdata / "hermes").exists()


def test_windows_hermes_appdata_not_adopted_when_no_douglas(monkeypatch, fake_home, tmp_path):
    """A sibling %LOCALAPPDATA%\\hermes (possibly a foreign, unrelated
    Hermes Agent install) must never be silently adopted — this is exactly
    the scenario that let a real Hermes.exe and Douglas Agent.exe collide
    on the same venv in production."""
    _set_platform(monkeypatch, windows=True)
    local_appdata = tmp_path / "AppData" / "Local"
    local_appdata.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))
    (local_appdata / "hermes").mkdir()

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_HOME"] == str(local_appdata / "douglas-agent")


def test_windows_legacy_home_hermes_not_adopted(monkeypatch, fake_home, tmp_path):
    """A pre-LOCALAPPDATA-era ~/.hermes existing is not adopted either —
    still defaults to %LOCALAPPDATA%\\douglas-agent."""
    _set_platform(monkeypatch, windows=True)
    local_appdata = tmp_path / "AppData" / "Local"
    local_appdata.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))
    (fake_home / ".hermes").mkdir()

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_HOME"] == str(local_appdata / "douglas-agent")


def test_windows_fresh_install_defaults_to_douglas_agent_appdata(monkeypatch, fake_home, tmp_path):
    _set_platform(monkeypatch, windows=True)
    local_appdata = tmp_path / "AppData" / "Local"
    local_appdata.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_HOME"] == str(local_appdata / "douglas-agent")


def test_windows_brand_detection_defaults_to_douglas_agent_when_not_under_hermes_root(monkeypatch, fake_home, tmp_path):
    """A checkout living anywhere other than %LOCALAPPDATA%\\hermes (a dev
    checkout, or a Douglas-branded install) defaults to douglas-agent — this
    is the common case and is already covered implicitly by every other
    test above, but is asserted directly here against the real
    brand-detection helper."""
    _set_platform(monkeypatch, windows=True)
    local_appdata = tmp_path / "AppData" / "Local"
    local_appdata.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))
    monkeypatch.setattr(hermes_bootstrap, "__file__", str(tmp_path / "some-checkout" / "hermes_bootstrap.py"))

    assert hermes_bootstrap._default_brand_home_dir_name() == "douglas-agent"


def test_windows_migrated_hermes_install_defaults_to_hermes_appdata(monkeypatch, fake_home, tmp_path):
    """The exact incident this helper exists for: a Hermes-branded install
    migrated to run this merged codebase still lives on disk under
    %LOCALAPPDATA%\\hermes — it must default to ITS OWN directory, not
    silently redirect into %LOCALAPPDATA%\\douglas and collide with a real
    Douglas Agent install's venv."""
    _set_platform(monkeypatch, windows=True)
    local_appdata = tmp_path / "AppData" / "Local"
    hermes_checkout = local_appdata / "hermes" / "hermes-agent"
    hermes_checkout.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))
    monkeypatch.setattr(hermes_bootstrap, "__file__", str(hermes_checkout / "hermes_bootstrap.py"))

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_HOME"] == str(local_appdata / "hermes")


def test_windows_without_localappdata_falls_back_to_home_style(monkeypatch, fake_home):
    """LOCALAPPDATA unset on Windows is an edge case, but must still resolve
    sensibly rather than crash — falls back to ~/.douglas-agent, same as
    POSIX, never adopting a sibling ~/.hermes."""
    _set_platform(monkeypatch, windows=True)
    (fake_home / ".hermes").mkdir()

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_HOME"] == str(fake_home / ".douglas-agent")


# ── Generic DOUGLAS_<X> -> HERMES_<X> variable aliasing ─────────────────────


def test_generic_douglas_var_aliases_to_hermes_var(monkeypatch, fake_home):
    _set_platform(monkeypatch, windows=False)
    monkeypatch.setenv("DOUGLAS_API_KEY", "douglas-secret")

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_API_KEY"] == "douglas-secret"


def test_generic_douglas_var_wins_when_both_set(monkeypatch, fake_home):
    _set_platform(monkeypatch, windows=False)
    monkeypatch.setenv("DOUGLAS_MODEL", "douglas-model")
    monkeypatch.setenv("HERMES_MODEL", "hermes-model")

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_MODEL"] == "douglas-model"


def test_hermes_var_untouched_when_no_douglas_equivalent(monkeypatch, fake_home):
    _set_platform(monkeypatch, windows=False)
    monkeypatch.setenv("HERMES_LANGUAGE", "es")

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_LANGUAGE"] == "es"


def test_empty_douglas_var_does_not_override_hermes_var(monkeypatch, fake_home):
    _set_platform(monkeypatch, windows=False)
    monkeypatch.setenv("DOUGLAS_PROFILE", "")
    monkeypatch.setenv("HERMES_PROFILE", "work")

    hermes_bootstrap.normalize_douglas_env()

    assert os.environ["HERMES_PROFILE"] == "work"


# ── ContextVar profile override still wins ──────────────────────────────────


def test_context_override_wins_over_normalized_env(monkeypatch, fake_home):
    """hermes_cli/profiles.py scopes a task to a profile via
    set_hermes_home_override(); that must keep winning over whatever
    normalize_douglas_env() put in os.environ["HERMES_HOME"], since the
    override is checked first and unconditionally inside get_hermes_home()."""
    _set_platform(monkeypatch, windows=False)
    monkeypatch.setenv("DOUGLAS_HOME", str(fake_home / "process-level-home"))
    hermes_bootstrap.normalize_douglas_env()
    assert os.environ["HERMES_HOME"] == str(fake_home / "process-level-home")

    profile_dir = fake_home / "profiles" / "acme-brand"
    token = hermes_constants.set_hermes_home_override(str(profile_dir))
    try:
        assert hermes_constants.get_hermes_home() == profile_dir
    finally:
        hermes_constants.reset_hermes_home_override(token)

    # With the override cleared, the process-level (normalized) value is
    # visible again.
    assert hermes_constants.get_hermes_home() == Path(os.environ["HERMES_HOME"])
