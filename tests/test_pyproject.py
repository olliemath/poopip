from __future__ import annotations

import re

import pytest

from poopip import normalize_name


def test_normalize_name() -> None:
    # Examples directly from
    # https://packaging.python.org/en/latest/specifications/name-normalization/
    for good in (
        "friendly-bard",
        "Friendly-Bard",
        "FRIENDLY-BARD",
        "friendly.bard",
        "friendly_bard",
        "friendly--bard",
        "FrIeNdLy-._.-bArD",
    ):
        # but we use the module/package friendly name
        assert normalize_name(good) == "friendly_bard"

    for bad in (
        "no spaces",
        "no'rm -rf *; special characters",
        "",  # no empty names
        "-no bad starts",
        "no bad ends_",
    ):
        with pytest.raises(SystemExit, match=re.escape(bad)):
            normalize_name(bad)

    assert normalize_name("0weird0") == "0weird0"
