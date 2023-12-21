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
poop install some/path/to/a/thing --user
# install in "editable" mode
poop develop some/path/to/a/thing
# uninstall package from current environment
poop uninstall thing
# uninstall user's global package
poop uninstall thing --user
```

## non-goals

poopip doesn't care about your package's requirements, just install them yourself (e.g. from a requirements.txt or requirements.lock file)

poopip doesn't aim to implement all of the [pypa specifications](https://packaging.python.org/en/latest/specifications/) - in particular, if you install a package with poopip it's a good idea to uninstall it with
poopip rather than relying on another packaging tool


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
| pypy3.10    | python poopip.py develop . | 0.116s |
| python3.11 | pip install --no-deps . | 1.981s |
| python3.11 | pip install --no-deps -e . | 1.920s |
| python3.11 | flit install --deps none  | 2.008s |
| python3.11 | flit install -s --deps none | 0.183s |
| python3.11 | python poopip install . | 0.061s |
| python3.11 | python poopip develop . | 0.075s |

Flit's not really a package manager, but it is much faster than pip if we use symlinks (`flit install -s --deps none`), so if you're after a good dev experience and only want to install in editable mode I would highly recomend it as a more sane option.
