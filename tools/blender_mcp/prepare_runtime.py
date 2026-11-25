"""Restore only the archived portable Python runtime into the install directory."""
from pathlib import Path, PurePosixPath
import sys
from zipfile import ZipFile

archive, output = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
if (output / 'python.exe').is_file():
    print('Portable Python already present:', output)
else:
    prefix = 'runtime/python/'
    count = 0
    with ZipFile(archive) as bundle:
        for member in bundle.infolist():
            if member.is_dir() or not member.filename.startswith(prefix):
                continue
            relative = PurePosixPath(member.filename[len(prefix):])
            destination = output.joinpath(*relative.parts).resolve()
            if not destination.is_relative_to(output):
                raise ValueError('Archive path escapes Python directory')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(bundle.read(member))
            count += 1
    assert (output / 'python.exe').is_file()
    print('Restored portable Python files:', count)
