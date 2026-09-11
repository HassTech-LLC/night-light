"""Preserve Windows owner/group/DACL before writing credential-bearing copies.

No privilege elevation or permissive fallback. A mismatch stops the write while
the temporary file is still empty. Auditing SACLs are not copied by this helper.
"""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
from functools import lru_cache
import os
from pathlib import Path
import tempfile
import hashlib
import re


@lru_cache(maxsize=1)
def _api():
    if os.name!='nt':raise OSError('Windows access-control support is required.')
    adv=ctypes.WinDLL('advapi32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    pointer=ctypes.c_void_p
    pointer_out=ctypes.POINTER(pointer)
    adv.GetNamedSecurityInfoW.argtypes=[wintypes.LPWSTR,wintypes.DWORD,wintypes.DWORD]+[pointer_out]*5
    adv.GetNamedSecurityInfoW.restype=wintypes.DWORD
    adv.SetNamedSecurityInfoW.argtypes=[wintypes.LPWSTR,wintypes.DWORD,wintypes.DWORD]+[pointer]*4
    adv.SetNamedSecurityInfoW.restype=wintypes.DWORD
    adv.GetSecurityDescriptorControl.argtypes=[pointer,ctypes.POINTER(wintypes.WORD),ctypes.POINTER(wintypes.DWORD)]
    adv.GetSecurityDescriptorControl.restype=wintypes.BOOL
    adv.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes=[pointer,wintypes.DWORD,wintypes.DWORD,pointer_out,ctypes.POINTER(wintypes.DWORD)]
    adv.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype=wintypes.BOOL
    kernel.LocalFree.argtypes=[pointer];kernel.LocalFree.restype=pointer
    return adv,kernel


def _sddl(descriptor):
    adv,kernel=_api();text=ctypes.c_void_p()
    if not adv.ConvertSecurityDescriptorToStringSecurityDescriptorW(descriptor,1,7,ctypes.byref(text),None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        value=ctypes.wstring_at(text)
        # SetNamedSecurityInfo can add SE_DACL_AUTO_INHERITED metadata when
        # propagating the already identical inherited ACEs. Ignore only that
        # history flag; retain protection, every ACE, ordering, owner and group.
        prefix,marker,dacl=value.partition('D:')
        flags,opening,entries=dacl.partition('(')
        return prefix+marker+flags.replace('AI','')+opening+entries
    finally:kernel.LocalFree(text)


@contextmanager
def _access(path):
    adv,kernel=_api()
    owner,group,dacl,descriptor=(ctypes.c_void_p() for _ in range(4))
    error=adv.GetNamedSecurityInfoW(str(path),1,7,ctypes.byref(owner),ctypes.byref(group),
                                  ctypes.byref(dacl),None,ctypes.byref(descriptor))
    if error:raise ctypes.WinError(error)
    try:
        if not dacl.value:raise OSError('A non-null access-control list is required.')
        control=wintypes.WORD();revision=wintypes.DWORD()
        if not adv.GetSecurityDescriptorControl(descriptor,ctypes.byref(control),ctypes.byref(revision)):
            raise ctypes.WinError(ctypes.get_last_error())
        yield owner,group,dacl,control.value,_sddl(descriptor)
    finally:kernel.LocalFree(descriptor)


def access_descriptor(path):
    """Internal verification value; do not include account SIDs in UI exports."""
    with _access(path) as access:return access[4]


def copy_file_access(source,target):
    adv,_=_api()
    with _access(source) as (owner,group,dacl,control,expected):
        protection=0x80000000 if control&0x1000 else 0x20000000
        error=adv.SetNamedSecurityInfoW(str(target),1,7|protection,owner,group,dacl,None)
        if error:raise ctypes.WinError(error)
        if access_descriptor(target)!=expected:
            raise OSError('Access-control verification failed; private write was stopped.')


def write_private_backup(source,target,payload):
    """Create one new same-directory copy; never replace an earlier backup."""
    source,target=Path(source),Path(target)
    if source.parent.resolve()!=target.parent.resolve():
        raise ValueError('Private backup must stay in the same directory.')
    if source.is_symlink() or target.is_symlink():raise ValueError('Linked backup paths are not supported.')
    if target.exists():raise FileExistsError(str(target))
    if not isinstance(payload,bytes):raise ValueError('Expected exact backup bytes.')
    fd,name=tempfile.mkstemp(prefix='.private-backup-',suffix='.tmp',dir=source.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            copy_file_access(source,name)
            stream.write(payload);stream.flush();os.fsync(stream.fileno())
        # Windows rename refuses an existing destination, unlike replace.
        os.rename(name,target)
        if target.read_bytes()!=payload:
            raise OSError('Private backup verification failed.')
    finally:
        if os.path.exists(name):os.unlink(name)


def retain_private_binary(access_source,binary,target,expected_digest):
    """Stream and verify a non-launchable rollback payload without replacement.

    Access follows the private configuration, not the public executable. This
    proves retained bytes, not signature validity or executable compatibility.
    """
    access_source,binary,target=map(Path,(access_source,binary,target))
    if not isinstance(expected_digest,str) or re.fullmatch('[0-9a-f]{64}',expected_digest) is None:
        raise ValueError('Expected a SHA-256 digest.')
    if target.parent.resolve()!=access_source.parent.resolve() or target.suffix!='.payload':
        raise ValueError('Retained binary must be a private same-directory payload.')
    if any(p.is_symlink() for p in (access_source,binary,target)):
        raise ValueError('Linked backup paths are not supported.')
    limit=1024*1024*1024
    def digest(path):
        result=hashlib.sha256();size=0
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):
                size+=len(block)
                if size>limit:raise OSError('Binary exceeds the retention size limit.')
                result.update(block)
        return result.hexdigest()
    expected_access=access_descriptor(access_source)
    if target.exists():
        if digest(target)!=expected_digest or access_descriptor(target)!=expected_access:
            raise OSError('Existing binary backup does not match; it was not replaced.')
        return
    fd,name=tempfile.mkstemp(prefix='.private-binary-',suffix='.tmp',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as output:
            copy_file_access(access_source,name)
            streamed=hashlib.sha256();size=0
            with binary.open('rb') as source:
                for block in iter(lambda:source.read(1024*1024),b''):
                    size+=len(block)
                    if size>limit:raise OSError('Binary exceeds the retention size limit.')
                    output.write(block);streamed.update(block)
            output.flush();os.fsync(output.fileno())
        if streamed.hexdigest()!=expected_digest or digest(Path(name))!=expected_digest:
            raise OSError('Source binary changed or retained bytes could not be verified.')
        if access_descriptor(name)!=expected_access:raise OSError('Binary access verification failed.')
        os.rename(name,target)
        if digest(target)!=expected_digest:raise OSError('Retained binary verification failed.')
    finally:
        if os.path.exists(name):os.unlink(name)
