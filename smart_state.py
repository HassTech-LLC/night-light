"""Versioned, immutable owner-state model. No native or persistence effects.

The owner persists before commit_saved, except Off which invalidates runtime
work first. resolve describes an intent, never claims a display write worked.
"""
from dataclasses import asdict, dataclass, field, fields, replace
import re
import secrets
from smart_transition import bounded, POLICY_VERSION

AVAILABILITY=frozenset(('available','windows_on','windows_unknown','external_conflict',
                        'unsupported','backend_error','unknown'))
LATCHED=frozenset(('external_conflict','unsupported','backend_error'))


def revision(value):
    if type(value) is not int or value<0:raise ValueError('Invalid revision.')
    return value


def identity(value):
    if not isinstance(value,str) or not 1<=len(value)<=128:raise ValueError('Invalid identity.')
    return value


def clock_text(value):
    if not isinstance(value,str) or re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]',value) is None:
        raise ValueError('Enter a time as HH:MM.')


@dataclass(frozen=True)
class Appearance:
    warmth_kelvin: float=4000.
    dim_fraction: float=0.

    def __post_init__(self):
        bounded(self.warmth_kelvin,1200,6500)
        bounded(self.dim_fraction,0,.8)


@dataclass(frozen=True)
class OutputObservation:
    requested_rgb: tuple | None=None
    accepted_rgb: tuple | None=None
    accepted_at: float | None=None
    readback_rgb: tuple | None=None
    readback_at: float | None=None
    readback_matrix: tuple | None=None
    current_confirmed: bool=False
    error: str | None=None

    def __post_init__(self):
        for rgb in (self.requested_rgb,self.accepted_rgb,self.readback_rgb):
            if rgb is not None:
                if not isinstance(rgb,tuple) or len(rgb)!=3:raise ValueError('Expected immutable RGB factors.')
                for value in rgb:bounded(value,0,1)
        for instant in (self.accepted_at,self.readback_at):
            if instant is not None:bounded(instant,0,1e15)
        if self.readback_matrix is not None:
            if not isinstance(self.readback_matrix,tuple) or len(self.readback_matrix)!=25:
                raise ValueError('Expected a complete immutable color matrix.')
            for value in self.readback_matrix:bounded(value,-1e6,1e6)
        if type(self.current_confirmed) is not bool:raise ValueError('Invalid confirmation flag.')
        if self.current_confirmed and self.accepted_rgb is None:raise ValueError('No accepted output to confirm.')
        if self.error is not None and (not isinstance(self.error,str) or len(self.error)>512):
            raise ValueError('Invalid output error.')

    def to_dict(self):
        return dict(requested_rgb=None if self.requested_rgb is None else list(self.requested_rgb),
                    accepted_rgb=None if self.accepted_rgb is None else list(self.accepted_rgb),
                    accepted_at=self.accepted_at,
                    readback_rgb=None if self.readback_rgb is None else list(self.readback_rgb),
                    readback_at=self.readback_at,
                    readback_matrix=None if self.readback_matrix is None else list(self.readback_matrix),
                    provenance='readback' if self.readback_matrix is not None or self.readback_rgb is not None else ('write_ack' if self.accepted_rgb is not None else 'unavailable'),
                    current_confirmed=self.current_confirmed,error=self.error)


@dataclass(frozen=True)
class SmartSettings:
    kind: str
    evening_ready: str='22:00'
    morning_neutral: str='07:00'
    warmth_kelvin: float=4000.
    dim_fraction: float=0.
    latitude: float | None=None
    longitude: float | None=None
    solar_offset_minutes: float=60.
    warmth_lead: float=180.
    dim_lead: float=60.
    slower: float=1.
    fallback_ready: str | None=None
    fallback_neutral: str | None=None
    timezone_policy: str='system'
    policy_version: str=POLICY_VERSION

    def __post_init__(self):
        if self.kind not in ('solar','personal'):raise ValueError('Choose solar or personal timing.')
        clock_text(self.evening_ready);clock_text(self.morning_neutral)
        if self.evening_ready==self.morning_neutral:raise ValueError('Evening and morning times must differ.')
        Appearance(self.warmth_kelvin,self.dim_fraction)
        bounded(self.solar_offset_minutes,-120,180)
        bounded(self.warmth_lead,60,240);bounded(self.dim_lead,15,120)
        if isinstance(self.slower,bool) or self.slower not in (.5,1.):raise ValueError('Invalid slower setting.')
        if self.timezone_policy!='system':raise ValueError('Use the Windows timezone.')
        if self.policy_version!=POLICY_VERSION:raise ValueError('Unsupported Smart policy version.')
        if (self.latitude is None)!=(self.longitude is None):raise ValueError('Enter both coordinates.')
        if self.latitude is not None:
            bounded(self.latitude,-90,90);bounded(self.longitude,-180,180)
        elif self.kind=='solar':raise ValueError('Solar timing needs a saved location.')
        if (self.fallback_ready is None)!=(self.fallback_neutral is None):raise ValueError('Enter both fallback times.')
        if self.fallback_ready is not None:
            clock_text(self.fallback_ready);clock_text(self.fallback_neutral)
            if self.fallback_ready==self.fallback_neutral:raise ValueError('Fallback times must differ.')

    @classmethod
    def from_dict(cls,value):
        if not isinstance(value,dict) or set(value)-{f.name for f in fields(cls)} or 'kind' not in value:
            raise ValueError('Invalid Smart settings fields.')
        return cls(**value)

    def to_dict(self):return asdict(self)

    @property
    def appearance(self):return Appearance(self.warmth_kelvin,self.dim_fraction)

    def plan(self,day,zone):
        """Pass only explicit validated preferences to the offline planner."""
        from smart_schedule import personal_plan, solar_plan
        comfort=dict(kelvin=self.warmth_kelvin,dim_fraction=self.dim_fraction,
                     warmth_lead=self.warmth_lead,dim_lead=self.dim_lead,slower=self.slower)
        if self.kind=='personal':
            return personal_plan(day,zone,self.evening_ready,self.morning_neutral,**comfort)
        fallback=None if self.fallback_ready is None else (self.fallback_ready,self.fallback_neutral)
        return solar_plan(day,zone,self.latitude,self.longitude,offset_minutes=self.solar_offset_minutes,
                          fallback=fallback,**comfort)


@dataclass(frozen=True)
class Override:
    kind: str
    expires_elapsed: float
    appearance: Appearance | None=None

    def __post_init__(self):
        if self.kind not in ('manual_hold','neutral_pause'):raise ValueError('Invalid override.')
        bounded(self.expires_elapsed,0,1e15)
        if self.kind=='manual_hold' and not isinstance(self.appearance,Appearance):raise ValueError('Appearance required.')
        if self.kind=='neutral_pause' and self.appearance is not None:raise ValueError('Pause must be neutral.')


@dataclass(frozen=True)
class Preview:
    token: str
    kind: str
    expires_elapsed: float
    appearance: Appearance | None=None

    def __post_init__(self):
        identity(self.token);bounded(self.expires_elapsed,0,1e15)
        if self.kind not in ('compare','comfort'):raise ValueError('Invalid preview.')
        if self.kind=='comfort' and not isinstance(self.appearance,Appearance):raise ValueError('Appearance required.')
        if self.kind=='compare' and self.appearance is not None:raise ValueError('Compare must be neutral.')


@dataclass(frozen=True)
class ControlState:
    owner_id: str=field(default_factory=lambda:secrets.token_hex(16),repr=False)
    mode: str='off'
    manual: Appearance=Appearance()
    settings: SmartSettings | None=None
    config_revision: int=0
    intent_revision: int=0
    generation: int=0
    availability: str='unknown'
    fault_latched: bool=False
    manual_resume_required: bool=False
    override: Override | None=None
    preview: Preview | None=None

    def __post_init__(self):
        identity(self.owner_id)
        if self.mode not in ('off','manual','smart'):raise ValueError('Invalid mode.')
        if not isinstance(self.availability,str) or self.availability not in AVAILABILITY:raise ValueError('Invalid availability.')
        for value in (self.config_revision,self.intent_revision,self.generation):revision(value)
        if not isinstance(self.manual,Appearance):raise ValueError('Invalid manual appearance.')
        if self.settings is not None and not isinstance(self.settings,SmartSettings):raise ValueError('Invalid settings.')
        if self.override is not None and (not isinstance(self.override,Override) or self.mode!='smart'):
            raise ValueError('Only Smart can have an override.')
        if self.preview is not None and not isinstance(self.preview,Preview):raise ValueError('Invalid preview.')
        if type(self.fault_latched) is not bool or type(self.manual_resume_required) is not bool:
            raise ValueError('Invalid availability flags.')

    def snapshot(self,session_id,sequence):
        # Typed allowlisted fields only, never arbitrary configuration values.
        identity(session_id);revision(sequence)
        values=asdict(self)
        values.pop('owner_id')
        return dict(protocol_version=2,session_id=session_id,sequence=sequence,**values)


@dataclass(frozen=True)
class OutputIntent:
    kind: str
    appearance: Appearance | None=None
    reason: str=''


def resolve(state):
    if state.availability!='available':return OutputIntent('none',reason=state.availability)
    if state.fault_latched:return OutputIntent('none',reason='retry_required')
    if state.preview is not None:
        return (OutputIntent('neutral',reason='compare') if state.preview.kind=='compare'
                else OutputIntent('appearance',state.preview.appearance,'comfort_preview'))
    if state.mode=='off':return OutputIntent('neutral',reason='off')
    if state.override is not None:
        return (OutputIntent('neutral',reason='pause') if state.override.kind=='neutral_pause'
                else OutputIntent('appearance',state.override.appearance,'temporary_adjustment'))
    if state.mode=='manual':
        if state.manual_resume_required:return OutputIntent('none',reason='resume_manual_required')
        return OutputIntent('appearance',state.manual,'manual')
    return OutputIntent('smart',reason='schedule')


@dataclass(frozen=True)
class Event:
    kind: str
    elapsed: float
    appearance: Appearance | None=None
    token: str | None=None
    availability: str | None=None


def reduce(state,event):
    now=bounded(event.elapsed,0,1e15)
    kind=event.kind
    def changed(*,intent=False,**patch):
        return replace(state,generation=state.generation+1,
                       intent_revision=state.intent_revision+int(intent),**patch)
    if kind=='off':
        return changed(intent=True,mode='off',preview=None,override=None,manual_resume_required=False)
    if kind in ('manual','adjust'):
        if not isinstance(event.appearance,Appearance):raise ValueError('Choose an appearance.')
        if kind=='adjust' and state.mode=='smart':
            return changed(preview=None,override=Override('manual_hold',now+3600,event.appearance))
        return changed(intent=True,mode='manual',manual=event.appearance,override=None,preview=None,
                       manual_resume_required=state.availability!='available' or state.fault_latched)
    if kind=='smart':
        return changed(intent=True,mode='smart',override=None,preview=None,manual_resume_required=False)
    if kind in ('pause','resume'):
        if state.mode!='smart':raise ValueError('Smart is not enabled.')
        return changed(preview=None,override=Override('neutral_pause',now+3600) if kind=='pause' else None)
    if kind in ('begin_compare','begin_comfort'):
        if state.availability!='available' or state.fault_latched:raise ValueError('Display adjustment is unavailable.')
        if kind=='begin_compare' and state.mode=='off':return state
        identity(event.token)
        comfort=kind=='begin_comfort'
        if comfort and not isinstance(event.appearance,Appearance):raise ValueError('Choose a preview appearance.')
        if state.preview is not None and event.token==state.preview.token:
            if state.preview.kind!=('comfort' if comfort else 'compare') or state.preview.appearance!=(event.appearance if comfort else None):
                raise ValueError('Preview identity was reused for different settings.')
            return state
        return changed(preview=Preview(event.token,'comfort' if comfort else 'compare',
                                       now+(20 if comfort else 10),event.appearance if comfort else None))
    if kind=='end_preview':
        identity(event.token)
        if state.preview is None or event.token!=state.preview.token:return state
        return changed(preview=None)
    if kind=='tick':
        preview=state.preview if state.preview is None or now<state.preview.expires_elapsed else None
        override=state.override if state.override is None or now<state.override.expires_elapsed else None
        if preview==state.preview and override==state.override:return state
        return changed(preview=preview,override=override)
    if kind=='availability':
        value=event.availability
        if not isinstance(value,str) or value not in AVAILABILITY:raise ValueError('Invalid availability.')
        if value==state.availability:return state
        return changed(availability=value,preview=None,
                       fault_latched=state.fault_latched or value in LATCHED,
                       manual_resume_required=state.manual_resume_required or (state.mode=='manual' and value!='available'))
    if kind=='retry':
        if state.availability!='available':raise ValueError('Display adjustment is still unavailable.')
        return changed(fault_latched=False,manual_resume_required=False,preview=None)
    if kind=='rebase':return changed(preview=None)
    raise ValueError('Unknown owner event.')


@dataclass(frozen=True)
class SaveTicket:
    owner_id: str
    generation: int
    config_revision: int
    settings: SmartSettings


def stage_save(state,settings,expected_revision):
    revision(expected_revision)
    if expected_revision!=state.config_revision:raise ValueError('Settings changed. Reload before saving.')
    if not isinstance(settings,SmartSettings):raise ValueError('Invalid Smart settings.')
    return SaveTicket(state.owner_id,state.generation,state.config_revision,settings)


def validate_save_ticket(state,ticket):
    if ticket.owner_id!=state.owner_id or ticket.generation!=state.generation or ticket.config_revision!=state.config_revision:
        raise ValueError('Intent or settings changed while saving. The earlier Save cannot enable Smart.')


def commit_saved(state,ticket,new_revision):
    validate_save_ticket(state,ticket);revision(new_revision)
    if new_revision<=state.config_revision:raise ValueError('Save was not confirmed by a new revision.')
    return replace(state,mode='smart',settings=ticket.settings,config_revision=new_revision,
                   intent_revision=state.intent_revision+1,generation=state.generation+1,
                   preview=None,override=None,manual_resume_required=False)
