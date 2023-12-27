from __future__ import annotations

import pytest

from poopip import _get_parser


def test_parser() -> None:
    parser = _get_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])

    args = parser.parse_args(["install", "foo"])
    assert args.command == "install"
    assert args.package == "foo"
    assert not args.editable
    assert not args.user

    args = parser.parse_args(["--user", "install", "-e", "bar"])
    assert args.command == "install"
    assert args.editable
    assert args.user

    args = parser.parse_args(["--user", "uninstall", "bar"])
    assert args.command == "uninstall"
    assert args.user

    args = parser.parse_args(["freeze"])
    assert args.command == "freeze"

    with pytest.raises(SystemExit):
        parser.parse_args(["blorp", "foo"])
