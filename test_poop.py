from __future__ import annotations

import pytest

from poop import _get_parser


def test_parser() -> None:
    parser = _get_parser()

    args = parser.parse_args(["install", "foo"])
    assert args.command == "install"
    assert args.package == "foo"
    assert not args.user

    args = parser.parse_args(["uninstall", "bar", "--user"])
    assert args.command == "uninstall"
    assert args.package == "bar"
    assert args.user

    args = parser.parse_args(["develop", "bar", "--user"])
    assert args.command == "develop"

    with pytest.raises(SystemExit):
        parser.parse_args(["blorp", "foo"])
