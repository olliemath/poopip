"""poopip: for when pip is too slow 💩"""
from __future__ import annotations

import os
import re
import shutil
import site
import stat
import sys
import zipfile
from argparse import ArgumentParser as _ArgumentParser, _StoreTrueAction
from pathlib import Path
from typing import NamedTuple

try:
    import tomllib  # type: ignore
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore


DisplayName = str
DistInfoName = str
ModuleName = str
_NAME_REX = re.compile(r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", re.IGNORECASE)
_REPLACE_REX = re.compile(r"[-._]+")
# pep503 name -> (actual name, version, dist-info path)
_SITE_INDEX: dict[str, tuple[str, str, Path]] = {}


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
        if location.name.endswith(".whl"):
            if editable:
                printerr(
                    "Error: 🕵️ looks like a wheel - can't install in editable mode 🤷"
                )

            install_wheel(location, user_flag)
        else:
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


def print_packages(user_flag: bool) -> None:
    """Print all installed packages"""
    target_dir = get_site_dir(user_flag)
    for name, version, _ in sorted(package_index(target_dir).values()):
        print(f"{name}=={version}")


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
    if user_flag:
        return Path(site.getusersitepackages())
    return Path(site.getsitepackages()[0])


def get_bin_dir(user_flag: bool) -> Path:
    """Get the env's binary path."""
    if user_flag:
        return Path(site.getuserbase()) / "bin"
    return Path(sys.executable).parent


def package_index(target_dir: Path) -> dict[str, tuple[str, str, Path]]:
    """Index installed packages in the form pep503 name -> (name, version, dist-info dir)."""
    if _SITE_INDEX:
        return _SITE_INDEX

    from email.parser import HeaderParser

    for candidate in target_dir.glob("*.dist-info"):
        if (meta := (candidate / "METADATA")).exists():
            with meta.open("r") as f:
                parsed = HeaderParser().parse(f)

            name = parsed.get("Name", "")
            version = parsed.get("Version", "")

            if name and version:
                _SITE_INDEX[normalize_name(name).lower()] = (name, version, candidate)

    return _SITE_INDEX


def find_installed(package: DisplayName, target_dir: Path) -> tuple[str, Path] | None:
    """List the installed version and distinfo path if it exists."""
    pep503name = normalize_name(package).lower()
    index = package_index(target_dir)

    if pep503name in index:
        return index[pep503name][1:]

    return None


def normalize_name(name: DisplayName) -> DistInfoName:
    """Normalize a package name into a filesystem name.

    NOTE: this is NOT the same as the definition used by PyPA. In particular
    we convert Some-Name to Some_Name rather than some-name. This is what is
    used for dist-info directory names. The module name is normally the
    "lowered" version of this.
    """
    if not _NAME_REX.fullmatch(name):
        printerr(f"Error: 🖍️ '{name}' is not a valid package name 🤷")

    return _REPLACE_REX.sub("_", name)


# === PyProject stuff === #
class PyProject(NamedTuple):
    name: DisplayName
    distinfo_name: DistInfoName
    module_name: ModuleName
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
    distinfo_name = normalize_name(name)
    module_name = distinfo_name.lower()

    # TODO: includes/excludes
    source = get_top_level(location, module_name)

    return PyProject(
        name=name,
        distinfo_name=distinfo_name,
        module_name=module_name,
        version=version,
        location=location,
        source=source,
        scripts=scripts,
    )


def get_top_level(location: Path, package: ModuleName) -> Path:
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

    if installed := find_installed(pyproject.name, target_dir):
        version, _ = installed
        if version == pyproject.version:
            return
        else:
            uninstall_impl(pyproject.name, target_dir)

    if editable:
        target = target_dir / (pyproject.module_name + ".pth")
        with target.open("w") as f:
            f.write(str(pyproject.source.parent.resolve()) + os.linesep)

    else:
        if pyproject.source.is_file():
            target = target_dir / (pyproject.module_name + ".py")
            shutil.copy2(pyproject.source, target)
        else:
            target = target_dir / pyproject.module_name
            shutil.copytree(pyproject.source, target, ignore=_IGNORE)

    install_scripts(pyproject.scripts, user_flag)
    install_metadata(location, pyproject, target_dir)


def install_wheel(location: Path, user_flag: bool) -> None:
    """Install a local python package from a wheel."""
    target_dir = get_site_dir(user_flag)

    name, version = parse_wheel_name(location.name)
    if installed_version := find_installed(name, target_dir):
        if installed_version == version:
            return
        else:
            uninstall_impl(name, target_dir)

    with zipfile.ZipFile(location, "r") as zf:
        zf.extractall(target_dir)

    dist_info = target_dir / f"{name}-{version}.dist-info"
    poopmark(dist_info)

    scripts = {}
    entry_points = dist_info / "entry_points.txt"
    if entry_points.exists():
        with entry_points.open("r") as f:
            for line in f:
                if " = " in line:
                    name, entry_point = line.split(" = ", 1)
                    scripts[name.strip()] = entry_point.strip()

    install_scripts(scripts, user_flag)


def poopmark(dist_info_dir: Path) -> None:
    with (dist_info_dir / "INSTALLER").open("w") as f:
        f.write("poopip" + os.linesep)


def parse_wheel_name(wheel_name: str) -> tuple[str, str]:
    """Parse a wheel name into details as outlined in PEP425."""
    # {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl

    if not wheel_name.endswith(".whl"):
        printerr(f"🤨 '{wheel_name}' doesn't look like a wheel 🤷")

    components = wheel_name.rsplit(".", 1)[0].split("-")
    if len(components) == 6:
        (
            distribution,
            version,
            _build_tag,
            _python_tag,
            _abi_tag,
            _platform_tag,
        ) = components
    elif len(components) == 5:
        distribution, version, _python_tag, _abi_tag, _platform_tag = components
    else:
        printerr(f"🤨 '{wheel_name}' doesn't look like a wheel 🤷")

    return distribution, version


def install_metadata(location: Path, pyproject: PyProject, target_dir: Path) -> None:
    """Write the project metadata to dist-info"""

    dist_info: Path = (
        target_dir / f"{pyproject.distinfo_name}-{pyproject.version}.dist-info"
    )
    dist_info.mkdir()

    poopmark(dist_info)
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

    with (dist_info / "top_level.txt").open("w") as f:
        f.write(pyproject.module_name + os.linesep)

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


def install_scripts(scripts: dict[str, str], user_flag: bool) -> None:
    bin = get_bin_dir(user_flag)
    bin.mkdir(exist_ok=True)

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


def uninstall_local(package: DisplayName, user_flag: bool) -> None:
    """Remove a package and its associated files."""
    target_dir = get_site_dir(user_flag)
    if not uninstall_impl(package, target_dir):
        printerr(f"👻 '{package}' not installed 🤷")


def uninstall_impl(package: DisplayName, target_dir: Path) -> bool:
    """Return True if something was uninstalled"""
    scripts = []
    top_level = []
    if installed := find_installed(package, target_dir):
        _, distinfo_dir = installed
        if (entry_points := distinfo_dir / "entry_points.txt").exists():
            with entry_points.open("r") as f:
                scripts = [line.split(" = ", 1)[0] for line in f if " = " in line]
        if (top_level_file := distinfo_dir / "top_level.txt").exists():
            with top_level_file.open("r") as f:
                top_level = [line.strip() for line in f if line.strip()]

        shutil.rmtree(distinfo_dir)

        bin = Path(sys.executable).parent
        for script in scripts:
            candidate: Path = bin / script
            candidate.unlink(missing_ok=True)

        for top in top_level:
            candidate = target_dir / (top + ".pth")
            if candidate.exists():
                candidate.unlink()
            else:
                candidate = target_dir / (top + ".py")
                if candidate.exists():
                    candidate.unlink()
                else:
                    candidate = target_dir / top
                    if candidate.exists():
                        shutil.rmtree(candidate)

        return True

    return False


if __name__ == "__main__":
    main()
