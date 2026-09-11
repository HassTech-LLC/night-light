"""Preview-gated migration planning and private transactional application.

The proposal stays in the native owner. A web payload must never be allowed to
manufacture its own preview approval. Persistent application additionally needs
the verified private backup/receipt transaction. Importing performs no I/O.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import re

from smart_state import Appearance, SmartSettings, clock_text, revision
from smart_transition import bounded, POLICY_VERSION


def uses_v2(config):
    return config.get('schema_version')==2 and config.get('migration_state')=='v2'


def _fingerprint(data):
    if not isinstance(data,dict):raise ValueError('Expected a configuration object.')
    return hashlib.sha256(json.dumps(data,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()


def _mode(data):
    if data.get('smart_enabled') is True:return 'smart'
    return 'manual' if data.get('enabled') is True else 'off'


def _manual(data):
    try:
        brightness=bounded(data.get('brightness',1.),.2,1.)
        return Appearance(data.get('temperature_k',3400),1-brightness)
    except ValueError:
        return None


def inspect_legacy(data):
    """Allowlisted UI inventory, not a configuration/history export."""
    _fingerprint(data)
    manual=_manual(data)
    location=None
    raw=data.get('smart_location')
    if isinstance(raw,dict):
        try:
            location=dict(latitude=bounded(raw.get('latitude'),-90,90),
                          longitude=bounded(raw.get('longitude'),-180,180))
            for field in ('city','country','postal'):
                value=raw.get(field)
                if isinstance(value,str) and len(value)<=128:location[field]=value
        except ValueError:location=None
    explicit={}
    bedtime=data.get('smart_bedtime')
    try:
        clock_text(bedtime);explicit['bedtime']=bedtime
    except ValueError:pass
    quiet=data.get('smart_quiet_hours')
    if isinstance(quiet,dict):
        try:
            clock_text(quiet.get('start'));clock_text(quiet.get('end'))
            if quiet['start']!=quiet['end']:
                explicit['quiet_start']=quiet['start'];explicit['quiet_end']=quiet['end']
        except ValueError:pass
    return dict(mode=_mode(data),manual=None if manual is None else asdict(manual),
                location=location,explicit_times=explicit,
                legacy_collection_enabled=data.get('smart_learning') is True,
                needs_manual_choice=manual is None,
                message_key='current_schedule_unchanged_preview_new_smart')


@dataclass(frozen=True)
class MigratedOverride:
    kind: str
    original_duration: float
    start_utc: str
    expiry_utc: str
    last_seen_utc: str
    appearance: Appearance | None


@dataclass(frozen=True)
class MigrationProposal:
    source_digest: str
    source_revision: int
    settings: SmartSettings
    manual: Appearance | None
    override: MigratedOverride | None=None


def propose_migration(data,settings,*,manual=None,now_utc=None,clear_override=False):
    if not isinstance(settings,SmartSettings):raise ValueError('Choose validated Smart preferences.')
    if manual is not None and not isinstance(manual,Appearance):raise ValueError('Choose a valid Manual appearance.')
    schema=data.get('schema_version',1)
    if type(schema) is not int or schema not in (1,2):raise ValueError('Unsupported configuration version.')
    if uses_v2(data):raise ValueError('This configuration already uses the new Smart policy.')
    chosen_manual=_manual(data) if manual is None else manual
    override=None
    if type(clear_override) is not bool:raise ValueError('Invalid override choice.')
    until=data.get('smart_hold_until',0)
    if until and not clear_override:
        until=bounded(until,0,1e15)
        if not isinstance(now_utc,datetime) or now_utc.utcoffset() is None:
            raise ValueError('A current clock sample is required to preview the existing pause or hold.')
        now_utc=now_utc.astimezone(timezone.utc)
        if until>now_utc.timestamp()+3600:
            raise ValueError('Existing override timing needs review; explicitly clear it or keep the current schedule.')
        if until>now_utc.timestamp() and _mode(data)=='smart':
            pause=data.get('smart_hold_kind')=='pause'
            override=MigratedOverride('neutral_pause' if pause else 'manual_hold',3600.,
                datetime.fromtimestamp(until-3600,timezone.utc).isoformat(),
                datetime.fromtimestamp(until,timezone.utc).isoformat(),now_utc.isoformat(),
                None if pause else chosen_manual)
    return MigrationProposal(_fingerprint(data),revision(data.get('config_revision',0)),settings,
                             chosen_manual,override)


def migration_patch(data,proposal,*,choice,previewed=False):
    if not isinstance(proposal,MigrationProposal):raise ValueError('A native migration proposal is required.')
    if choice not in ('keep','switch'):raise ValueError('Choose whether to keep or switch your schedule.')
    if proposal.source_digest!=_fingerprint(data) or proposal.source_revision!=revision(data.get('config_revision',0)):
        raise ValueError('Settings changed since this preview. Review the new proposal.')
    if choice=='keep':return {}
    if previewed is not True:raise ValueError('Review the new schedule preview before switching.')
    if proposal.manual is None:raise ValueError('Choose a supported Manual appearance before switching.')
    # Preserve the raw values, including unknown extensions, for compatible
    # rollback/migration inspection. The active credential stays in one place.
    legacy=deepcopy(data)
    legacy.pop('ipc_token',None)
    legacy.pop('legacy_v1',None)
    return dict(schema_version=2,migration_state='v2',policy_version=POLICY_VERSION,
                intent_v2=dict(mode=_mode(data),manual=asdict(proposal.manual)),
                smart_settings_v2=proposal.settings.to_dict(),
                override_v2=None if proposal.override is None else asdict(proposal.override),
                legacy_v1=legacy,smart_learning=False,
                enabled=False,smart_enabled=False,smart_hold_until=0,
                migration_consent_version=2,
                onboarding_v2=dict(version=2,flow='upgrade',completed=False))


def new_install_patch():
    """Only for a positively identified fresh install, not guessed from Off."""
    return dict(schema_version=2,migration_state='v2',policy_version=POLICY_VERSION,
                intent_v2=dict(mode='off',manual=asdict(Appearance())),
                smart_settings_v2=SmartSettings(kind='personal').to_dict(),override_v2=None,
                enabled=False,smart_enabled=False,smart_learning=False,
                temperature_k=4000,brightness=1.,autostart=False,
                onboarding_v2=dict(version=2,flow='first_run',completed=False))


def initialize_first_install(config):
    """Initialize only a config this process proved it created from defaults.

    Existing Off users, imported settings and concurrent writers never become
    new installs merely because a version marker is missing.
    """
    from config_manager import DEFAULT_CONFIG
    if not config.created_new or uses_v2(config):return False
    if set(config.data)-set(DEFAULT_CONFIG)-{'ipc_token','config_revision'}:return False
    if any(config.get(key)!=value for key,value in DEFAULT_CONFIG.items()):return False
    config.transactional_update(new_install_patch(),expected_revision=config.get('config_revision',0))
    config.created_new=False
    return True


def commit_migration(config,proposal,*,previewed,binary_path,before_commit=None):
    """Worker-side migration transaction; never changes the native display.

    Retains verified binary/config bytes. The installer must still validate
    compatibility/signatures and implement deliberate executable rollback.
    """
    from pathlib import Path
    from config_manager import config_file_lock
    from private_config_files import access_descriptor,write_private_backup,retain_private_binary
    binary=Path(binary_path)
    if binary.is_symlink() or not binary.is_file() or binary.stat().st_size>1024*1024*1024:
        raise ValueError('A bounded source application artifact is required.')
    binary_digest=hashlib.sha256()
    binary_size=0
    with binary.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            binary_size+=len(chunk)
            if binary_size>1024*1024*1024:raise ValueError('Source artifact grew beyond the size limit.')
            binary_digest.update(chunk)
    with config._lock,config_file_lock(config.file_path):
        if before_commit is not None:before_commit()
        if config.file_path.stat().st_size>2*1024*1024:
            raise ValueError('Configuration is too large for automatic migration.')
        original=config.file_path.read_bytes()
        disk=json.loads(original.decode('utf-8'))
        patch=migration_patch(disk,proposal,choice='switch',previewed=previewed)
        # Reject unflushed local edits as well as a different on-disk revision.
        if _fingerprint(config.data)!=proposal.source_digest:
            raise ValueError('Local settings changed since the migration preview.')
        digest=hashlib.sha256(original).hexdigest()
        backup=config.file_path.with_name(f'config.pre-v2-{digest}.json')
        expected_access=access_descriptor(config.file_path)
        def preserve(path,payload):
            if path.exists():
                if path.is_symlink() or path.read_bytes()!=payload or access_descriptor(path)!=expected_access:
                    raise OSError('Existing migration backup does not match; source was not changed.')
            else:write_private_backup(config.file_path,path,payload)
        preserve(backup,original)
        binary_sha=binary_digest.hexdigest()
        retained=config.file_path.with_name(f'application.pre-v2-{binary_sha}.payload')
        retain_private_binary(config.file_path,binary,retained,binary_sha)
        receipt=dict(version=2,config_backup=backup.name,config_sha256=digest,
                     source_revision=proposal.source_revision,
                     source_binary_sha256=binary_sha,binary_retained=True,binary_backup=retained.name,
                     policy_version=POLICY_VERSION)
        receipt_path=config.file_path.with_name(f'config-migration-v2-{digest}-{binary_sha}.receipt.json')
        preserve(receipt_path,json.dumps(receipt,sort_keys=True,indent=2).encode())
        candidate=deepcopy(config.data)
        candidate.update(patch)
        candidate['migration_receipt']=receipt
        config._save_locked(candidate=candidate,before_commit=before_commit)
        if config._debounce_timer:
            config._debounce_timer.cancel();config._debounce_timer=None
        return deepcopy(receipt)


def verify_retained_migration_files(config):
    """Read-only verification before a future explicit installer rollback.

    Neither executes a payload nor restores settings. Never accepts paths from
    a receipt unless they exactly match the expected content-addressed names.
    """
    from private_config_files import access_descriptor
    receipt=config.get('migration_receipt')
    if not isinstance(receipt,dict) or type(receipt.get('version')) is not int or receipt['version']!=2 or receipt.get('binary_retained') is not True:
        raise ValueError('No retained migration pair is recorded.')
    config_sha=receipt.get('config_sha256');binary_sha=receipt.get('source_binary_sha256')
    for value in (config_sha,binary_sha):
        if not isinstance(value,str) or re.fullmatch('[0-9a-f]{64}',value) is None:raise ValueError('Invalid backup digest.')
    names={'config_backup':f'config.pre-v2-{config_sha}.json',
           'binary_backup':f'application.pre-v2-{binary_sha}.payload'}
    expected_access=access_descriptor(config.file_path)
    config_bytes=bytearray()
    for key,expected in names.items():
        if receipt.get(key)!=expected:raise ValueError('Backup path does not match its content identity.')
        path=config.file_path.parent/expected
        if path.is_symlink() or not path.is_file():raise OSError('Retained migration file is missing or linked.')
        if access_descriptor(path)!=expected_access:raise OSError('Retained migration access controls do not match.')
        limit=2*1024*1024 if key=='config_backup' else 1024*1024*1024
        digest=hashlib.sha256();size=0
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):
                size+=len(block)
                if size>limit:raise OSError('Retained migration file exceeds its size limit.')
                digest.update(block)
                if key=='config_backup':config_bytes.extend(block)
        if digest.hexdigest()!=(config_sha if key=='config_backup' else binary_sha):
            raise OSError('Retained migration bytes do not match the receipt.')
    original=json.loads(config_bytes.decode('utf-8'))
    source_revision=revision(receipt.get('source_revision'))
    if not isinstance(original,dict) or original.get('config_revision',0)!=source_revision:
        raise ValueError('Retained configuration revision does not match.')
    return dict(bytes_verified=True,source_revision=source_revision,config_sha256=config_sha,
                source_binary_sha256=binary_sha,signature_verified=False,activation_verified=False)
