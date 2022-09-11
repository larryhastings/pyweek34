"""Build a distribution from the PyWeek entry."""

from contextlib import ExitStack
from fnmatch import fnmatch
from pathlib import Path
import sys
from typing import Optional
import zipfile


class Package:
    ZIPOPTS = {}
    def __init__(self, dest_path: Path):
        self.dest_path = dest_path
        self.rootdir = Path(dest_path.stem)
        self.ctx = ExitStack()
        self.zip = self.ctx.enter_context(
            zipfile.ZipFile(
                self.ctx.enter_context(dest_path.open('wb')),
                mode='w',
                compression=zipfile.ZIP_DEFLATED,
            )
        )

    def add_files(self, *paths: str):
        for p in paths:
            self.zip.write(p, self.rootdir / p, **self.ZIPOPTS)

    def add_text(self, dest: str, data: str):
        self.zip.writestr(str(self.rootdir / dest), data)

    def add_directory(
        self,
        root: str,
        dest: Optional[str] = None,
        pattern: str = '**/*',
        exclude: list[str] = [
            '__pycache__',
        ]
    ):
        dest = self.rootdir / (dest or root)
        root = Path(root)
        for path in root.glob(pattern):
            relpath = path.relative_to(root)
            if any(pat in str(relpath) for pat in exclude):
                continue
            self.zip.write(
                path,
                dest / (relpath),
                 **self.ZIPOPTS
            )

    def __enter__(self) -> 'Package':
        return self

    def __exit__(self, cls, inst, tb) -> None:
        self.ctx.close()
        if inst:
            self.dest_path.unlink()


def build_package(dest_path: Path):
    with Package(dest_path) as p:
        p.add_files(
            'pyfxrsounds.py',
            'main.py',
            'collision.py',
            'AUTHORS.md',
            'README.md',
            'LICENSE',
        )
        p.add_directory(
            'vendor/wasabi2d/wasabi2d',
            'wasabi2d',
        )

        reqs = sorted(set(
            open('requirements.txt').readlines() +
            open('vendor/wasabi2d/requirements.txt').readlines()
        ))
        filtered_reqs = ''.join(r for r in reqs if not r.startswith('-e vendor/'))
        p.add_text('requirements.txt', filtered_reqs)

        for dir in ('sounds', 'fonts', 'data'):
            p.add_directory(dir)

        p.add_directory('images', pattern='*')
        p.add_files(
            'images/pixel_platformer/Pixel Platformer.tsx',
            'images/pixel_platformer/License.txt',
        )
        p.add_directory('images/pixel_platformer/tiles')


build_package(Path(sys.argv[1]))
