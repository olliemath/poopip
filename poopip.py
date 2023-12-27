"""poopip: for when pip is too slow 💩"""
from __future__ import annotations

import os
import shutil
import stat
import sys
from argparse import ArgumentParser as _ArgumentParser, _StoreTrueAction
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

try:
    import tomllib  # type: ignore
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

if TYPE_CHECKING:
    from collections.abc import Iterator


DangerousName = str
SafeName = str
_EVENTUAL_NAME_REX = None
_EVENTUAL_REPLACE_REX = None


def main() -> None:
    parser = _get_parser()
    args = parser.parse_args()
    if args.command == "install":
        install(args.package, editable=args.editable, user_flag=args.user)
    elif args.command == "uninstall":
        uninstall(args.package, user_flag=args.user)
    elif args.command == "freeze":
        print_packages(user_flag=args.user)


def install(package: str, editable: bool = True, user_flag: bool = False) -> None:
    """Install a local package.

    Essentially we will just copy or symlink this to the correct site-packages
    directory. I'm not sure how something so simple got so complicated?
    """
    location = Path(package).resolve()
    if not location.exists():
        printerr(f"Error: 🕵️ couldn't find '{package}' 🤷")

    try:
        install_local(location, editable, user_flag)
    except PermissionError:
        printerr(
            "Error: 👮 insufficient permissions to write 🤷 try working in a venv?",
            code=3,
        )


def uninstall(package: str, user_flag: bool = False) -> None:
    """Uninstall a local package."""
    try:
        uninstall_local(package, user_flag)
    except PermissionError:
        printerr(
            "Error: 👮 insufficient permissions to remove 🤷 try working in a venv?",
            code=3,
        )


def _get_parser() -> _ArgumentParser:
    """Build and return a decent-ish arg parser."""

    parser = _ArgumentParser(
        prog="poop",
        description="""install local pure python packages super quickly!
        for when pip is too slow 💩 and you're not doing anything fancy 🧐 """,
        epilog="""pip is advanced and complex 🔬 for serious professionals 🤵
        poop is basic and simple 🔨 for impatient children 🦄""",
    )
    parser.add_argument(
        "--user", action=_StoreTrueAction, help="use user-local packages"
    )
    subparsers = parser.add_subparsers(
        title="command", description="command to run", dest="command", required=True
    )

    install_parser = subparsers.add_parser("install", help="install a package")
    install_parser.add_argument("package", type=str, help="name or path of the package")
    install_parser.add_argument(
        "-e", "--editable", action=_StoreTrueAction, help="install in editable mode"
    )

    uninstall_parser = subparsers.add_parser("uninstall", help="uninstall a package")
    uninstall_parser.add_argument(
        "package", type=str, help="name or path of the package"
    )

    subparsers.add_parser("freeze", help="show installed packages")

    return parser


# === Logging and IO === #
def printerr(err: str, code: int = 1) -> None:
    """Print a message and exit with the given code"""
    print(err, file=sys.stderr)
    exit(code)


# === Site dir and package utils === #
def get_site_dir(user_flag: bool) -> Path:
    """Get the site packages directory."""
    import site

    if user_flag:
        return Path(site.getusersitepackages())
    return Path(site.getsitepackages()[0])


def list_packages(target_dir: Path) -> Iterator[tuple[str, str]]:
    """List installed packages in the form (name, version)."""
    from email.parser import HeaderParser

    for candidate in target_dir.glob("*.dist-info"):
        if (meta := (candidate / "METADATA")).exists():
            with meta.open("r") as f:
                parsed = HeaderParser().parse(f)

            name = parsed.get("Name", "")
            version = parsed.get("Version", "")

            if name and version:
                yield name, version


def find_installed(
    package: DangerousName, target_dir: Path
) -> tuple[SafeName, str] | None:
    """List the installed package name and version, or None if it does not exist"""
    from email.parser import HeaderParser

    package = normalize_name(package)
    candidate: Path
    for candidate in target_dir.glob(f"{package}-*.dist-info"):
        if (meta := (candidate / "METADATA")).exists():
            with meta.open("r") as f:
                parsed = HeaderParser().parse(f)

            if normalize_name(parsed.get("Name", "")) == package:
                if version := parsed.get("Version", ""):
                    return package, version

    return None


def normalize_name(name: DangerousName) -> SafeName:
    """Normalize a package name into a filesystem name.

    NOTE: this is NOT the same as the definition used by PyPA. In particular
    we convert to some_name rather than some-name.
    """
    import re

    global _EVENTUAL_NAME_REX, _EVENTUAL_REPLACE_REX
    if _EVENTUAL_NAME_REX is None:
        _EVENTUAL_NAME_REX = re.compile(
            r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", re.IGNORECASE
        )
        _EVENTUAL_REPLACE_REX = re.compile(r"[-._]+")

    if not _EVENTUAL_NAME_REX.fullmatch(name):
        printerr(f"Error: 🖍️ '{name}' is not a valid package name 🤷")

    return _EVENTUAL_REPLACE_REX.sub("_", name).lower()


# === PyProject stuff === #
class PyProject(NamedTuple):
    name: DangerousName
    normalize_name: SafeName
    version: str
    location: Path
    source: Path
    scripts: dict[str, str]


def parse_pyproject(location: Path) -> PyProject:
    with (location / "pyproject.toml").open("rb") as f:
        raw = tomllib.load(f)["project"]

    name: str = raw["name"]
    version: str = raw.get("version", "0.0.0")

    for bad_key in ("gui-scripts", "entry-points", "dynamic"):
        if raw.get(bad_key):
            raise NotImplementedError(
                f"{bad_key} section not yet implemented\n"
                "use another tool to install this project"
            )

    scripts = raw.get("scripts", {})
    normalized_name = normalize_name(name)

    # TODO: includes/excludes
    source = get_top_level(location, normalized_name)

    return PyProject(
        name=name,
        normalize_name=normalized_name,
        version=version,
        location=location,
        source=source,
        scripts=scripts,
    )


def get_top_level(location: Path, package: SafeName) -> Path:
    """Determine the top-level file/directory for the package.

    We try only package.py, src/package.py, package/ and src/package/
    """
    for file_candidate in (
        location / (package + ".py"),
        location / "src" / (package + ".py"),
    ):
        if file_candidate.exists() and file_candidate.is_file():
            return file_candidate

    for dir_candidate in (location / package, location / "src" / package):
        if dir_candidate.exists() and dir_candidate.is_dir():
            return dir_candidate

    printerr("Error: 🔖 incorrectly labelled or non-existant source 🤷")
    # XXX: the following is unreachable, but satisfies mypy
    return None  # type: ignore


# === Actual install/uninstall routines ===
_IGNORE = shutil.ignore_patterns("tests", "test_*.py")


def install_local(location: Path, editable: bool, user_flag: bool) -> None:
    """Install a pure-python local package."""

    pyproject = parse_pyproject(location)
    target_dir = get_site_dir(user_flag)

    if installed_version := find_installed(pyproject.name, target_dir):
        if installed_version == pyproject.version:
            return
        else:
            uninstall_impl(pyproject.name, target_dir)

    if editable:
        target = target_dir / (pyproject.normalize_name + ".pth")
        with target.open("w") as f:
            f.write(str(pyproject.source.parent.resolve()) + os.linesep)

    else:
        if pyproject.source.is_file():
            target = target_dir / (pyproject.normalize_name + ".py")
            shutil.copy2(pyproject.source, target)
        else:
            target = target_dir / pyproject.normalize_name
            shutil.copytree(pyproject.source, target, ignore=_IGNORE)

    install_scripts(pyproject.scripts)
    install_metadata(location, pyproject, target_dir)


def install_metadata(location: Path, pyproject: PyProject, target_dir: Path) -> None:
    """Write the project metadata to dist-info"""

    dist_info: Path = (
        target_dir / f"{pyproject.normalize_name}-{pyproject.version}.dist-info"
    )
    dist_info.mkdir()

    with (dist_info / "INSTALLER").open("w") as f:
        f.write("poopip" + os.linesep)

    with (dist_info / "METADATA").open("w") as f:
        f.write(
            os.linesep.join(
                [
                    "Metadata-Version: 2.1",
                    f"Name: {pyproject.name}",
                    f"Version: {pyproject.version}",
                ]
            )
        )

    with (dist_info / "entry_points.txt").open("w") as f:
        f.write("[console_scripts]" + os.linesep)
        f.writelines(f"{k} = {v}{os.linesep}" for k, v in pyproject.scripts.items())

    # Look for a LICENSE and AUTHORS file if they exist
    license: Path
    for license_candidate in ("LICENSE", "LICENSE.txt"):
        if (license := location / license_candidate).exists():
            shutil.copy2(license, dist_info)
            break

    authors: Path
    for authors_candidate in ("AUTHORS", "AUTHORS.txt"):
        if (authors := location / authors_candidate).exists():
            shutil.copy2(authors, dist_info)
            break


def install_scripts(scripts: dict[str, str]) -> None:
    bin = Path(sys.executable).parent
    for name, spec in scripts.items():
        module, func = spec.split(":")

        script: Path = bin / name
        with script.open("w") as f:
            f.write(
                f"""#!{sys.executable}
# -*- coding: utf-8 -*-
import re
import sys
from {module} import {func}
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\\.pyw|\\.exe)?$', '', sys.argv[0])
    sys.exit({func}())
"""
            )

        # make our script executable
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def uninstall_local(package: DangerousName, user_flag: bool) -> None:
    """Remove a package and its associated files."""
    target_dir = get_site_dir(user_flag)
    if not uninstall_impl(package, target_dir):
        printerr(f"👻 '{package}' not installed 🤷")


def uninstall_impl(package: DangerousName, target_dir: Path) -> bool:
    """Return True if something was uninstalled"""
    scripts = []
    if installed := find_installed(package, target_dir):
        safe_name, version = installed
        meta_dir = target_dir / f"{safe_name}-{version}.dist-info"
        if (entry_points := meta_dir / "entry_points.txt").exists():
            with entry_points.open("r") as f:
                for line in f:
                    if " = " in line:
                        scripts.append(line.split(" = ", 1)[0])

        shutil.rmtree(meta_dir)

        bin = Path(sys.executable).parent
        for script in scripts:
            candidate = bin / script
            candidate.unlink(missing_ok=True)

        candidate = target_dir / (package + ".pth")
        if candidate.exists():
            candidate.unlink(missing_ok=True)
        else:
            candidate = target_dir / (package + ".py")
            if candidate.exists():
                candidate.unlink(missing_ok=True)
            else:
                candidate = target_dir / package
                if candidate.exists():
                    shutil.rmtree(candidate)

        return True

    return False


def print_packages(user_flag: bool) -> None:
    target_dir = get_site_dir(user_flag)
    for name, version in sorted(list_packages(target_dir)):
        print(f"{name}=={version}")


if __name__ == "__main__":
    main()
