from __future__ import annotations

import pathlib
import tempfile

import pytest

from poopip import _get_parser, _parse_pyproject


def test_parser() -> None:
    parser = _get_parser()

    args = parser.parse_args(["install", "foo"])
    assert args.command == "install"
    assert args.package == "foo"
    assert not args.user

    args = parser.parse_args(["develop", "bar", "--user"])
    assert args.command == "develop"
    assert args.user

    args = parser.parse_args(["uninstall", "bar"])
    assert args.command == "uninstall"

    with pytest.raises(SystemExit):
        parser.parse_args(["blorp", "foo"])


def test_parse_pyproject() -> None:
    path = pathlib.Path(__file__).parent
    assert _parse_pyproject(path) == ("0.1.0", {"poop": "poopip:main"})

    with tempfile.TemporaryDirectory() as d:
        path = pathlib.Path(d)
        assert _parse_pyproject(path) == ("0.0.0", {})
