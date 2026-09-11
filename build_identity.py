"""Build-time identity, never inferred from online release metadata."""
import hashlib
import json
from pathlib import Path
import re
import sys

PRODUCT_ID='com.hasstech.night-light'


def make_identity(manifest,version,runtime):
    files=manifest['files']
    if not files:raise ValueError('Source inventory is required.')
    digest=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return dict(schema=1,product_id=PRODUCT_ID,version=version,build_id=digest[:16],
                source_sha256=digest,source_revision=manifest.get('git_head'),
                dirty=manifest.get('tracked_worktree_dirty'),runtime=runtime,
                channel='private-candidate')


def running_identity():
    """Source runs never borrow an identity left behind by a packaged build."""
    if not getattr(sys,'frozen',False):
        return dict(kind='development',label='Source development run',verified=False)
    try:
        path=Path(sys._MEIPASS)/'assets'/'BUILD-IDENTITY.json'
        if path.stat().st_size>16384:raise ValueError('Oversized receipt.')
        value=json.loads(path.read_text(encoding='utf-8'))
        if (value.get('schema')!=1 or value.get('product_id')!=PRODUCT_ID
                or value.get('channel')!='private-candidate'
                or not re.fullmatch(r'[0-9a-f]{64}',value.get('source_sha256',''))
                or value.get('build_id')!=value['source_sha256'][:16]
                or not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?',value.get('version',''))):
            raise ValueError('Invalid build identity.')
        return dict(kind='packaged',label='Packaged private candidate',verified=False,
                    version=value['version'],build_id=value['build_id'],source_sha256=value['source_sha256'],
                    source_revision=value.get('source_revision'),dirty=value.get('dirty'),
                    channel=value['channel'])
    except (OSError,ValueError,AttributeError,TypeError):
        return dict(kind='unknown',label='Build identity unavailable',verified=False)
