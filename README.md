# poopip: for when pip is too slow 💩

poopip is a tiny python package installer/uninstaller
designed for working on local (i.e. already in your filesystem) pure python packages

poopip has very few features, but this makes it fast! 🔥


## get poopip

assuming you have your favorite virtual environemnt already set up, you can run

```bash
pip install poopip
```

or else you can clone this repo and issue

```
python poopip/poopip.py install poopip/
```

## usage

for `some/path/to/a/package` the following should work:

```bash
# install to our current environment
poop install some/path/to/a/thing
# install globally for current user
poop --user install some/path/to/a/thing
# install in "editable" mode
poop install -e some/path/to/a/thing
# uninstall package from current environment
poop uninstall thing
# uninstall user's global package
poop --user uninstall thing
```

generally poopip will take the name of the directory as the name of the package and
assume the code is either at thing/thing.py, or a directory thing/thing/ - it's on
our todo list to read the pyproject.toml for this.


## goals

- fast: aims to be the fastest step in your dev/ci process
- small: single file under 1000 lines of code
- portable: pure python, zero dependencies
- readable: reading the source code will tell you something about how installs work

On the portability front, currently poopip only officially supports linux - contributions are welcome.


## non-goals

- requirements: poopip doesn't care about your package's requirements, just use a requirements file and install them yourself
- [pypa specifications](https://packaging.python.org/en/latest/specifications/): poopip doesn't aim to implement all of the specifications where they conflict with its goals
- setup.py: we have no intention of supporting setup.py or even dynamic pyproject fields

Note that while poopip understands and can update or uninstall pip-installed packages the converse is not true. The reason is that poopip's metadata operates at the directory level, whereas pip relies upon a list of individual files - creating this list is slow with large packages, so we don't do it. Use poopip to unistall poopip-installed packages.


## benchmarks

Here's how long it takes to install poopip itself (a zero-dependency, single python file) with various tools.
In the regular old install case, poopip is up to 300x faster than pip!

| interpreter | command | time |
| ----------- | ------- | ---- |
| pypy3.10    | pip install --no-deps . | 5.645s |
| pypy3.10    | pip install --no-deps -e . | 5.983s |
| pypy3.10    | flit install --deps none | 6.143s |
| pypy3.10    | flit install -s --deps none | 0.415s |
| pypy3.10    | python poopip.py install . | 0.136s |
| pypy3.10    | python poopip.py install -e . | 0.116s |
| python3.11 | pip install --no-deps . | 1.981s |
| python3.11 | pip install --no-deps -e . | 1.920s |
| python3.11 | flit install --deps none  | 2.008s |
| python3.11 | flit install -s --deps none | 0.183s |
| python3.11 | python poopip install . | 0.061s |
| python3.11 | python poopip install -e . | 0.075s |

Flit's not really a package manager, but it is much faster than pip if we use symlinks (`flit install -s --deps none`), so if you're after a good dev experience and only want to install in editable mode I would highly recomend it as a more sane option.
