#!/usr/bin/env python3
"""Catalog intake: find new dfpc-coe ETLs, new release tags, and moved community pins.

It only reports. It keeps one open issue titled "Catalog intake" up to date (or closes it when
there is nothing to do). It has no signing key, so it can never change what a server installs:
every change still needs a security review and an offline signature.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

ORG = 'dfpc-coe'
NOT_ETLS = {'etl-base', 'etl-template'}      # libraries
HIDDEN = {'etl-drone-tag'}                   # empty template, posts nothing
SEMVER = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)$')
TITLE = 'Catalog intake'
TOKEN = os.environ.get('GITHUB_TOKEN', '')
REPO = os.environ.get('GITHUB_REPOSITORY', 'takwerx/infratak-etl-catalog')


def api(path, method='GET', body=None):
    url = path if path.startswith('https://') else f'https://api.github.com/{path}'
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={'Accept': 'application/vnd.github+json',
                                          'User-Agent': 'infratak-etl-catalog-intake',
                                          **({'Authorization': f'Bearer {TOKEN}'} if TOKEN else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read() or b'null')
        nxt = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get('Link') or '')
    if nxt and isinstance(data, list):
        data += api(nxt.group(1))
    return data


def vkey(v):
    m = SEMVER.match(v or '')
    return tuple(int(x) for x in m.groups()) if m else None


def highest_tag(full):
    tags = [(vkey(t['name']), t['name'], t['commit']['sha']) for t in api(f'repos/{full}/tags?per_page=100')]
    tags = [t for t in tags if t[0]]
    return max(tags) if tags else None


def findings(cat):
    by_src = {e['source']: e for e in cat['entries']}
    out = []
    repos = [r for r in api(f'orgs/{ORG}/repos?per_page=100')
             if r['name'].startswith('etl-') and r['name'] not in NOT_ETLS | HIDDEN
             and not r['archived'] and not r['private']]
    seen = set()
    for r in sorted(repos, key=lambda r: r['name']):
        full = r['full_name']
        seen.add(full)
        t = highest_tag(full)
        e = by_src.get(full)
        if not t:
            continue
        if e is None:
            out.append(f'- **NEW** [{full}](https://github.com/{full}) {t[1]} (`{t[2][:12]}`)')
        elif t[0] > (vkey(e['version']) or (0, 0, 0)):
            out.append(f"- **BUMP** `{e['prefix']}` {e['version']} -> {t[1]} (`{t[2][:12]}`) "
                       f"[diff](https://github.com/{full}/compare/{e['sha']}...{t[2]})")
    for e in cat['entries']:
        if e['source'].startswith(f'{ORG}/') and e['source'] not in seen:
            out.append(f"- **GONE** `{e['prefix']}` ({e['source']} is archived, private or deleted)")
        if e.get('community'):
            t = highest_tag(e['source'])
            if t and t[0] > (vkey(e['version']) or (0, 0, 0)):
                out.append(f"- **BUMP** `{e['prefix']}` {e['version']} -> {t[1]} (community, `{t[2][:12]}`)")
            elif not SEMVER.match(e.get('ref') or ''):
                try:
                    head = api(f"repos/{e['source']}/branches/{e['ref']}")['commit']['sha']
                except urllib.error.HTTPError:
                    head = None
                if head and head != e['sha']:
                    out.append(f"- **MOVED** `{e['prefix']}` branch `{e['ref']}` is now `{head[:12]}` "
                               f"(pinned `{e['sha'][:12]}`) "
                               f"[diff](https://github.com/{e['source']}/compare/{e['sha']}...{head})")
    return out


def main():
    cat = json.load(open('catalog.json'))
    lines = findings(cat)
    body = ('Found by the daily intake check. Nothing here is installable until it passes the '
            'security review and the catalog is signed again.\n\n' + '\n'.join(lines)) if lines else ''
    print(body or 'catalog is current')
    if '--report' not in sys.argv:
        return
    open_issues = [i for i in api(f'repos/{REPO}/issues?state=open&per_page=100')
                   if i['title'] == TITLE and 'pull_request' not in i]
    if lines and open_issues:
        if open_issues[0]['body'] != body:
            api(f"repos/{REPO}/issues/{open_issues[0]['number']}", 'PATCH', {'body': body})
    elif lines:
        api(f'repos/{REPO}/issues', 'POST', {'title': TITLE, 'body': body})
    for i in open_issues if not lines else []:
        api(f"repos/{REPO}/issues/{i['number']}", 'PATCH', {'state': 'closed', 'state_reason': 'completed'})


if __name__ == '__main__':
    main()
