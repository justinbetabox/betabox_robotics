"""Provision private curriculum copies without replacing existing notebooks."""
from __future__ import annotations

import base64
import json
import os
import stat
import subprocess
from collections.abc import Iterable
from pathlib import Path

from betabox_robotics.services.accounts import BETABOX_ACCOUNTS, ProvisionedAccount
from betabox_robotics.services.workspace import account_ids

TEACHER_ROOT = Path('/var/lib/betabox/curriculum/teacher')
UNITS = {
    'unit01_python_foundations': 8,
    'unit02_programming_your_car': 11,
}

# Run only this copying step as the recipient, not as root. Students cannot
# use workspace symlinks to make the installer write privileged files.
_COPY = r'''
import base64
import json
import os
import sys
import tempfile
from pathlib import Path

payload = json.load(sys.stdin)
root = Path(payload['destination'])
for relative, encoded in payload['files'].items():
    target = root / relative
    for directory in target.parents:
        if directory.is_symlink():
            raise RuntimeError(f'Unexpected symlink: {directory}')
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if target.is_symlink():
        raise RuntimeError(f'Unexpected notebook symlink: {target}')
    if target.exists():
        if not target.is_file():
            raise RuntimeError(f'Not a regular notebook: {target}')
        continue
    # Publish a fully written file atomically; never replace another file.
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temp:
        temporary = Path(temp.name)
        try:
            temp.write(base64.b64decode(encoded))
            temp.flush()
            os.fsync(temp.fileno())
            os.fchmod(temp.fileno(), 0o600)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        try:
            os.link(temporary, target, follow_symlinks=False)
        except FileExistsError:
            if target.is_symlink() or not target.is_file():
                raise RuntimeError(f'Unsafe existing notebook: {target}')
    finally:
        temporary.unlink(missing_ok=True)
'''


def _load_notebooks(root: Path) -> dict[str, str]:
    """Read only lesson notebooks in the two known curriculum units."""
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError(f'Missing or unsafe curriculum directory: {root}')
    result: dict[str, str] = {}
    for unit, minimum in UNITS.items():
        directory = root / unit
        if directory.is_symlink() or not directory.is_dir():
            raise RuntimeError(f'Missing or unsafe curriculum unit: {directory}')
        paths = sorted(directory.glob('lesson*.ipynb'))
        if len(paths) < minimum:
            raise RuntimeError(f'{directory}: expected at least {minimum} lessons')
        for path in paths:
            if path.is_symlink() or not path.is_file():
                raise RuntimeError(f'Unsafe notebook source: {path}')
            result[f'{unit}/{path.name}'] = base64.b64encode(path.read_bytes()).decode('ascii')
    return result


def _check_teacher_source() -> None:
    """Refuse to use publicly readable or symlinked instructor assets."""
    for directory in (TEACHER_ROOT.parent, TEACHER_ROOT):
        if directory.is_symlink() or not directory.is_dir():
            raise RuntimeError(f'Stage the private teacher curriculum first: {directory}')
        info = directory.stat()
        if info.st_uid != 0 or stat.S_IMODE(info.st_mode) & 0o077:
            raise RuntimeError(f'Teacher directory must be root-owned and mode 0700: {directory}')
    for directory in TEACHER_ROOT.parents:
        if directory.is_symlink():
            raise RuntimeError(f'Unexpected symlink in teacher source: {directory}')


def _copy_for_account(account: ProvisionedAccount, destination: Path, notebooks: dict[str, str]) -> None:
    uid, gid = account_ids(account.username)
    if uid == 0 or gid == 0:
        raise RuntimeError(f'Refusing to copy curriculum as a privileged account: {account.username}')
    subprocess.run(
        ['/usr/bin/python3', '-I', '-c', _COPY],
        input=json.dumps({'destination': str(destination), 'files': notebooks}),
        text=True,
        check=True,
        user=uid,
        group=gid,
        extra_groups=[],
        cwd='/',
        umask=0o077,
        env={'PATH': '/usr/bin:/bin', 'HOME': str(account.home)},
    )


def populate_curriculum(
    repository_root: str | Path,
    *,
    accounts: Iterable[ProvisionedAccount] = BETABOX_ACCOUNTS,
) -> None:
    """Install student templates and admin-only completed lessons.

    The private teacher package must be staged before full provisioning.
    Guest-only provisioning does not require or read the teacher package.
    Existing files are preserved, including on installer reruns.
    """
    if os.geteuid() != 0:
        raise PermissionError('Curriculum provisioning requires root.')
    managed = tuple(accounts)
    allowed = {a.username: a.home for a in BETABOX_ACCOUNTS}
    for account in managed:
        if allowed.get(account.username) != account.home:
            raise RuntimeError(f'Unexpected managed account: {account.username}')
    templates = _load_notebooks(Path(repository_root) / 'curriculum')
    teacher = None
    if any(account.username == 'admin' for account in managed):
        _check_teacher_source()
        teacher = _load_notebooks(TEACHER_ROOT)
        if teacher.keys() != templates.keys():
            raise RuntimeError('Teacher and student lesson filenames must match exactly.')
    for account in managed:
        destination = account.home / 'curriculum'
        if account.username == 'admin':
            assert teacher is not None
            _copy_for_account(account, destination / 'templates', templates)
            _copy_for_account(account, destination / 'completed', teacher)
        else:
            _copy_for_account(account, destination, templates)
        print(f'Curriculum provisioned: {account.username} (existing notebooks preserved)')
