from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import venv
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any


@pytest.fixture(scope="session")
def repo() -> pathlib.Path:
    return pathlib.Path(__file__).parent.resolve()


@pytest.fixture()
def venv_env() -> Iterator[dict[str, str]]:
    """Create an isolated venv for this test"""
    with tempfile.TemporaryDirectory() as tempdir:
        venv_dir = pathlib.Path(tempdir) / "venv"
        venv.create(venv_dir)

        env = dict(os.environ)
        env["VIRTUAL_ENV"] = str(venv_dir)
        env["PATH"] = str(venv_dir / "bin") + ":" + env["PATH"]

        yield env


def run_command(cmd: list[Any], env: dict[str, str]) -> None:
    subprocess.check_call(list(map(str, cmd)), env=env, stderr=sys.stderr)


def test_install_develop_uninstall_mixed(
    venv_env: dict[str, str], repo: pathlib.Path
) -> None:
    # first let's install poop itself
    run_command(["python", repo / "poop.py", "install", repo], env=venv_env)
    # now check we can run it
    run_command(["poop", "--help"], env=venv_env)
    # this should be a no-op
    run_command(["python", repo / "poop.py", "install", repo], env=venv_env)
    run_command(["python", repo / "poop.py", "develop", repo], env=venv_env)
    assert str(repo) not in sys.path  # should not have overriden the install
    # we can still run the script
    run_command(["poop", "--help"], env=venv_env)
    # now let's uninstall
    run_command(["python", repo / "poop.py", "uninstall", "poop"], env=venv_env)
    # we can no longer run the script
    with pytest.raises(subprocess.CalledProcessError):
        run_command(["poop", "--help"], env=venv_env)

    # now let's do the same with develop
    run_command(["python", repo / "poop.py", "develop", repo], env=venv_env)
    # now check we can run it
    run_command(["poop", "--help"], env=venv_env)
    # this should be a no-op
    run_command(["python", repo / "poop.py", "develop", repo], env=venv_env)
    run_command(["python", repo / "poop.py", "install", repo], env=venv_env)
    assert str(repo) in sys.path  # should not have overriden the install
    # we can still run the script
    run_command(["poop", "--help"], env=venv_env)
    # now let's uninstall
    run_command(["python", repo / "poop.py", "uninstall", "poop"], env=venv_env)
    # we can no longer run the script
    with pytest.raises(subprocess.CalledProcessError):
        run_command(["poop", "--help"], env=venv_env)
