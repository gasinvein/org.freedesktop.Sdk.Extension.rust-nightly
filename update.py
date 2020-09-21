#!/usr/bin/env python3

import argparse
import datetime
import json
import logging
import sys
import urllib.parse
import urllib.request

HISTORY_URL = 'https://rust-lang.github.io/rustup-components-history'
DIST_URL = 'https://static.rust-lang.org/dist'
RUST_ARCHES = {
    'x86_64': 'x86_64-unknown-linux-gnu',
    'i386': 'i686-unknown-linux-gnu',
    'aarch64': 'aarch64-unknown-linux-gnu',
    'arm': 'arm-unknown-linux-gnueabihf'
}
REQUIRED_COMPONENTS = ['rust', 'cargo', 'rust-std', 'rustc', 'rustc-dev', 'rustfmt']


def get_history(target: str, component: str) -> list:
    avail_url = f'{HISTORY_URL}/{target}/{component}.json'
    try:
        with urllib.request.urlopen(avail_url) as resp:
            history_json = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    last_available = datetime.date.fromisoformat(history_json.pop('last_available'))
    history = [datetime.date.fromisoformat(d) for d, a in history_json.items() if a]
    assert last_available in history
    return sorted(history)


def get_last_available(components=REQUIRED_COMPONENTS) -> datetime.date:
    avail_builds = None
    for rust_arch in RUST_ARCHES.values():
        for comp in components:
            logging.info(f'Checking {comp} availability for {rust_arch}')
            comp_history = get_history(rust_arch, comp)
            if avail_builds is None:
                avail_builds = set(comp_history)
            else:
                avail_builds = avail_builds & set(comp_history)
    assert avail_builds
    return max(avail_builds)


def get_build_source(date: datetime.date, arch: str, component: str, suffix='-nightly') -> dict:
    target = RUST_ARCHES[arch]
    #assert date in get_history(target, component)
    url = f'{DIST_URL}/{date.isoformat()}/{component}{suffix}-{target}.tar.xz'
    with urllib.request.urlopen(f'{url}.sha256') as resp:
        sha256, _ = resp.read().decode().split()
    return {
        'type': 'archive',
        'only-arches': [arch],
        'url': url,
        'sha256': sha256
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', default='generated-sources.json')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    last_available = get_last_available()
    sources = []
    for arch in RUST_ARCHES:
        sources.append(get_build_source(last_available, arch, 'rust'))

    with open(args.output, 'w') as o:
        json.dump(sources, o, indent=4)
    sys.stdout.write(last_available.isoformat())



if __name__ == '__main__':
    main()
