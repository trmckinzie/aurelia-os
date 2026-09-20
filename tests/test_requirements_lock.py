"""requirements*.in are the hand-edited pins; requirements*.txt are the hashed
lock files CI installs with --require-hashes. Nothing regenerates the lock
automatically, so these tests fail when the two drift apart -- a pin bumped in
a .in file without recompiling, or a lock entry that lost its hashes."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_IN_PIN = re.compile(r"^([A-Za-z0-9._-]+)==([^\s;#]+)")
# A lock entry: name==version, optionally an environment marker, then the
# first --hash line continuing on the next line.
_LOCK_ENTRY = re.compile(r"^([A-Za-z0-9._-]+)==([^\s;]+)[^\n]*\\\n((?:\s+--hash=sha256:[0-9a-f]{64}[ \\]*\n?)+)", re.M)


def _norm(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def _read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return fh.read()


def _pins(in_name, seen=None):
    """Exact pins from a .in file, following `-r other.in` includes."""
    seen = seen if seen is not None else set()
    pins = {}
    for line in _read(in_name).splitlines():
        line = line.strip()
        include = re.match(r"^-r\s+(\S+)", line)
        if include and include.group(1) not in seen:
            seen.add(include.group(1))
            pins.update(_pins(include.group(1), seen))
            continue
        match = _IN_PIN.match(line)
        if match:
            pins[_norm(match.group(1))] = match.group(2)
    return pins


def _lock(txt_name):
    return {_norm(m.group(1)): m.group(2) for m in _LOCK_ENTRY.finditer(_read(txt_name))}


def test_every_lock_entry_carries_hashes():
    for txt_name in ("requirements.txt", "requirements-dev.txt"):
        text = _read(txt_name)
        # Every pinned line must be one _LOCK_ENTRY recognises, i.e. followed
        # by at least one sha256 hash. A bare `name==1.2.3` would let pip
        # install it unverified if --require-hashes were ever dropped.
        pinned_lines = re.findall(r"^[A-Za-z0-9._-]+==", text, re.M)
        assert len(_lock(txt_name)) == len(pinned_lines), txt_name
        assert pinned_lines, f"{txt_name} has no pinned packages"


def test_lock_files_match_their_in_files():
    for in_name, txt_name in (
        ("requirements.in", "requirements.txt"),
        ("requirements-dev.in", "requirements-dev.txt"),
    ):
        lock = _lock(txt_name)
        for name, version in _pins(in_name).items():
            assert lock.get(name) == version, (
                f"{txt_name} has {name}=={lock.get(name)} but {in_name} pins {version}; "
                f"recompile with the command in the file's header"
            )


def test_dev_lock_contains_the_whole_runtime_lock():
    runtime, dev = _lock("requirements.txt"), _lock("requirements-dev.txt")
    for name, version in runtime.items():
        assert dev.get(name) == version, f"{name} differs between the runtime and dev locks"
