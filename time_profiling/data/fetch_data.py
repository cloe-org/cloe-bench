"""Download the time_profiling input data from Zenodo into this folder and verify it.

    python fetch_data.py                 # download, extract, verify against MANIFEST.sha256
    python fetch_data.py --verify-only   # only check the files already here
    python fetch_data.py --archive time_profiling_data_v1.tar.gz   # use a local copy of the archive

Plain stdlib. The archive is the one made by make_zenodo_bundle.sh. MANIFEST.sha256 (committed) is the
reference, so a corrupted or outdated download fails loudly.
"""
import argparse
import hashlib
import os
import sys
import tarfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
# TODO: fill in after the first upload (Zenodo record -> Files -> link of the archive), and the DOI in README.md
ZENODO_URL = os.environ.get('TP_ZENODO_URL', 'https://zenodo.org/records/<RECORD_ID>/files/time_profiling_data_v1.tar.gz')


def verify():
    manifest = (HERE / 'MANIFEST.sha256').read_text().split('\n')
    bad = []
    for line in filter(None, manifest):
        digest, name = line.split(maxsplit=1)
        path = HERE / name
        if not path.exists():
            bad.append(f'missing  {name}')
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            bad.append(f'checksum {name}')
    if bad:
        sys.exit('Data check failed:\n  ' + '\n  '.join(bad))
    print(f'OK: {len(list(filter(None, manifest)))} files match MANIFEST.sha256 in {HERE}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verify-only', action='store_true')
    ap.add_argument('--archive', help='local archive instead of downloading')
    args = ap.parse_args()
    if not args.verify_only:
        archive = Path(args.archive) if args.archive else HERE / Path(ZENODO_URL).name
        if not archive.exists():
            if '<RECORD_ID>' in ZENODO_URL:
                sys.exit('The Zenodo record is not set yet: set TP_ZENODO_URL or ZENODO_URL in fetch_data.py.')
            print(f'downloading {ZENODO_URL}')
            urllib.request.urlretrieve(ZENODO_URL, archive)
        with tarfile.open(archive) as tar:
            members = [m for m in tar.getmembers() if m.name != 'MANIFEST.sha256']   # keep the committed one
            for m in members:
                if m.name.startswith('/') or '..' in Path(m.name).parts:
                    sys.exit(f'refusing to extract {m.name}')
            extra = {'filter': 'data'} if hasattr(tarfile, 'data_filter') else {}   # Python >= 3.12 (and backports)
            tar.extractall(HERE, members=members, **extra)
    verify()


if __name__ == '__main__':
    main()
