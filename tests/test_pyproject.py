from __future__ import annotations

import pytest

from poopip import normalize_name


def test_normalize_name() -> None:
    # Examples directly from
    # https://packaging.python.org/en/latest/specifications/name-normalization/
    for good, expected in (
        ("friendly-bard", "friendly_bard"),
        ("Friendly-Bard", "Friendly_Bard"),
        ("FRIENDLY-BARD", "FRIENDLY_BARD"),
        ("friendly.bard", "friendly_bard"),
        ("friendly_bard", "friendly_bard"),
        ("friendly--bard", "friendly_bard"),
        ("FrIeNdLy-._.-bArD", "FrIeNdLy_bArD"),
    ):
        # but we use the module/package friendly name
        assert normalize_name(good) == expected

    for bad in (
        "no spaces",
        "no'rm -rf *; special characters",
        "",  # no empty names
        "-no bad starts",
        "no bad ends_",
    ):
        with pytest.raises(SystemExit):
            normalize_name(bad)

    assert normalize_name("0weird0") == "0weird0"
