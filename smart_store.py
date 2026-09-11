"""Owner-thread persistence coordinator for explicitly selected v2 installs.

This does not silently migrate legacy users. Replies concern durable settings,
not successful display output. The final commit guard cannot call config APIs.
"""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import timedelta
import hashlib
import json
import threading

from smart_state import identity, stage_save, validate_save_ticket


class SmartStore:
    def __init__(self, owner, config):
        self.owner, self.config = owner, config
        self._thread = threading.get_ident()
        self._recent = OrderedDict()

    def _assert_owner(self):
        if threading.get_ident() != self._thread:
            raise RuntimeError('Commit commands must run on the resident owner thread.')

    def _prepare(self, settings, expected_revision, session_id, request_id):
        self._assert_owner()
        identity(session_id); identity(request_id)
        if self.config.get('schema_version') != 2 or self.config.get('migration_state') != 'v2':
            raise ValueError('Explicit migration or new-install setup is required first.')
        # Validate before hashing or consulting idempotency records.
        from smart_state import SmartSettings
        if not isinstance(settings, SmartSettings):
            raise ValueError('Validated Smart settings required.')
        canonical = settings.to_dict()
        digest = hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        key = (session_id, request_id)
        cached = self._recent.get(key)
        receipt = self.config.get('last_smart_save')
        if cached is None and isinstance(receipt,dict) and (receipt.get('session_id'),receipt.get('request_id')) == key:
            revision = receipt.get('saved_revision')
            if type(revision) is int and 0 < revision <= self.config.get('config_revision',0):
                cached = (receipt.get('digest'),dict(outcome='saved',config_revision=revision,
                                                  settings=deepcopy(canonical)))
        if cached is not None:
            if cached[0] != digest:
                raise ValueError('Request identity was reused for different settings.')
            # Historical acknowledgement only: never replay the output action.
            return dict(cached=deepcopy(cached[1]),key=key,digest=digest)
        if self.config.automatic_output_blocked:
            raise OSError('Repair session recovery storage before enabling Smart.')
        ticket = stage_save(self.owner.state, settings, expected_revision)
        predicted_revision = expected_revision + 1
        receipt = dict(session_id=session_id,request_id=request_id,digest=digest,
                       saved_revision=predicted_revision,settings=canonical)
        patch = dict(schema_version=2,migration_state='v2',policy_version=settings.policy_version,
                     intent_v2=dict(mode='smart',manual=asdict(self.owner.state.manual)),
                     smart_settings_v2=canonical,override_v2=None,last_smart_save=receipt,
                     enabled=False,smart_enabled=False,smart_hold_until=0)
        onboarding=self.config.get('onboarding_v2')
        if isinstance(onboarding,dict) and onboarding.get('version')==2:
            patch['onboarding_v2']=dict(onboarding,completed=True)
        # Compatibility flags stay neutral. Only the v2 owner interprets v2
        # intent; rollback still requires the matching pre-migration config.
        return dict(cached=None,key=key,digest=digest,ticket=ticket,patch=patch,canonical=canonical)

    def _complete(self, prepared, revision):
        self.owner.accept_saved(prepared['ticket'],revision)
        result = dict(outcome='saved',config_revision=revision,settings=prepared['canonical'])
        self._recent[prepared['key']] = (prepared['digest'],deepcopy(result))
        while len(self._recent)>128:
            self._recent.popitem(last=False)
        return result

    def save(self, settings, expected_revision, session_id, request_id):
        prepared=self._prepare(settings,expected_revision,session_id,request_id)
        if prepared['cached'] is not None:return prepared['cached']
        ticket=prepared['ticket']
        self.config.transactional_update(prepared['patch'],expected_revision=expected_revision,
            before_commit=lambda:validate_save_ticket(self.owner.state,ticket))
        revision = self.config.get('config_revision')
        return self._complete(prepared,revision)

    def off(self):
        self._assert_owner()
        accepted = self.owner.command('off')
        try:
            self.config.transactional_update(self.config.off_patch())
        except (OSError,ValueError):
            return dict(outcome='off_not_saved',output_accepted=bool(accepted))
        self.owner.state = replace(self.owner.state,config_revision=self.config.get('config_revision',0))
        return dict(outcome='off_saved',output_accepted=bool(accepted),
                    config_revision=self.owner.state.config_revision)


class SaveSuperseded(ValueError):
    pass


class AsyncSmartStore(SmartStore):
    """Serial disk worker; native effects and replies are finalized by poll().

    Off invalidates leases and requests neutral on the owner immediately, then
    queues its persistence after any already-committing write. A Save that won
    the filesystem race cannot win the later owner-generation check.
    """
    def __init__(self, owner, config):
        super().__init__(owner,config)
        self._worker=ThreadPoolExecutor(max_workers=1,thread_name_prefix='NightLight-settings')
        self._jobs=OrderedDict()
        self._closed=False
        self._command_recent=OrderedDict()
        self._unsubscribe=owner.observe_invalidation(self._invalidate)

    def _invalidate(self):
        for job in self._jobs.values():
            if job['kind']=='save':job['cancelled'].set()
            elif job['kind']=='command' and job['signature']!=self._intent_signature():
                job['cancelled'].set()

    def _intent_signature(self):
        state=self.owner.state
        return state.mode,state.manual,state.settings,state.override

    def _intent_patch(self):
        state=self.owner.state
        override=None
        if state.override is not None:
            sample=self.owner.last_sample
            remaining=max(0.,min(3600.,state.override.expires_elapsed-sample.elapsed_seconds))
            expiry=sample.utc+timedelta(seconds=remaining)
            override=dict(kind=state.override.kind,original_duration=3600,
                          start_utc=(expiry-timedelta(hours=1)).isoformat(),
                          expiry_utc=expiry.isoformat(),last_seen_utc=sample.utc.isoformat(),
                          appearance=asdict(state.override.appearance) if state.override.appearance else None)
        return dict(intent_v2=dict(mode=state.mode,manual=asdict(state.manual)),
                    smart_settings_v2=state.settings.to_dict(),policy_version=state.settings.policy_version,
                    override_v2=override,
                    enabled=False,smart_enabled=False,smart_hold_until=0)

    def submit_command(self,kind,session_id,request_id,appearance=None):
        """Apply explicit intent on owner, serialize its durability off-thread.

        Unlike Save, these controls take effect immediately; a storage failure
        is reported separately and prevents a misleading clean-exit receipt.
        Retransmitted identities acknowledge history without replaying output.
        """
        self._assert_owner()
        identity(session_id);identity(request_id)
        if kind not in ('manual','adjust','smart','pause','resume'):
            raise ValueError('Unsupported persistent command.')
        key=(session_id,request_id);payload=(kind,appearance)
        prior=self._command_recent.get(key)
        if prior is not None:
            if prior[0]!=payload:raise ValueError('Request identity was reused for different settings.')
            return deepcopy(prior[1])
        if key in self._jobs:
            job=self._jobs[key]
            if job['kind']!='command' or job['payload']!=payload:
                raise ValueError('Request identity was reused for different settings.')
            return dict(outcome='command_saving',session_id=session_id,request_id=request_id)
        if self._closed:raise RuntimeError('Settings worker is closed.')
        if len(self._jobs)>=32:raise ValueError('Too many pending settings requests.')
        if self.config.get('schema_version')!=2 or self.config.get('migration_state')!='v2':
            raise ValueError('Explicit v2 setup is required.')
        if self.config.automatic_output_blocked:
            raise OSError('Repair recovery storage before enabling output.')
        self.owner.command(kind,appearance)
        patch=self._intent_patch()
        cancelled=threading.Event()
        def guard():
            if cancelled.is_set():raise SaveSuperseded('Newer intent wins.')
        def persist():
            guard()
            return self.config.transactional_update_isolated(patch,before_commit=guard)
        self.config.owner_commit_pending=True
        job=dict(kind='command',payload=payload,signature=self._intent_signature(),cancelled=cancelled)
        self._jobs[key]=job
        job['future']=self._worker.submit(persist)
        return dict(outcome='command_saving',session_id=session_id,request_id=request_id)

    def save(self,*args,**kwargs):
        raise RuntimeError('Use submit_save on the asynchronous store.')

    def off(self,*args,**kwargs):
        raise RuntimeError('Use submit_off on the asynchronous store.')

    def submit_save(self,settings,expected_revision,session_id,request_id):
        self._assert_owner()
        if self._closed:raise RuntimeError('Settings worker is closed.')
        key=(session_id,request_id)
        # Check pending identity before the durable receipt cache. A finished
        # disk job still needs exactly one owner-thread completion.
        if key in self._jobs:
            job=self._jobs[key]
            if job['kind']!='save' or settings!=job['prepared']['ticket'].settings:
                raise ValueError('Request identity was reused for different settings.')
            return dict(outcome='saving',session_id=session_id,request_id=request_id)
        prepared=self._prepare(settings,expected_revision,session_id,request_id)
        if prepared['cached'] is not None:
            return dict(prepared['cached'],session_id=session_id,request_id=request_id)
        if len(self._jobs)>=32:raise ValueError('Too many pending settings requests.')
        cancelled=threading.Event()
        def guard():
            if cancelled.is_set():raise SaveSuperseded('Intent changed before saving.')
        def persist():
            guard()
            return self.config.transactional_update_isolated(prepared['patch'],
                expected_revision=expected_revision,before_commit=guard)
        job=dict(kind='save',prepared=prepared,cancelled=cancelled)
        self.config.owner_commit_pending=True
        self._jobs[key]=job
        job['future']=self._worker.submit(persist)
        return dict(outcome='saving',session_id=session_id,request_id=request_id)

    def submit_off(self,session_id,request_id):
        self._assert_owner()
        identity(session_id);identity(request_id)
        accepted=self.owner.command('off')
        self.config.owner_commit_pending=True
        key=(session_id,request_id)
        if key in self._jobs and self._jobs[key]['kind']=='off':
            return dict(outcome='off_saving',session_id=session_id,request_id=request_id,output_accepted=bool(accepted))
        if self._closed or len(self._jobs)>=32 or key in self._jobs:
            return dict(outcome='off_not_saved',session_id=session_id,request_id=request_id,output_accepted=bool(accepted))
        # Read the patch on the worker after preceding writes, preserving the
        # latest chosen Manual appearance and unrelated fields.
        future=self._worker.submit(lambda:self.config.transactional_update_isolated(self.config.off_patch()))
        self._jobs[key]=dict(kind='off',future=future,output_accepted=bool(accepted))
        return dict(outcome='off_saving',session_id=session_id,request_id=request_id,output_accepted=bool(accepted))

    def poll(self):
        self._assert_owner()
        replies=[]
        for key,job in list(self._jobs.items()):
            if not job['future'].done():continue
            del self._jobs[key]
            persisted=False
            try:
                revision=job['future'].result()
                persisted=True
                if job['kind']=='save':
                    if job['cancelled'].is_set():raise SaveSuperseded('Newer intent wins.')
                    validate_save_ticket(self.owner.state,job['prepared']['ticket'])
                    result=self._complete(job['prepared'],revision)
                else:
                    if job['kind']=='command' and job['cancelled'].is_set():
                        raise SaveSuperseded('Newer intent wins.')
                    if revision>self.owner.state.config_revision:
                        self.owner.state=replace(self.owner.state,config_revision=revision)
                    result=(dict(outcome='command_saved',config_revision=revision) if job['kind']=='command'
                            else dict(outcome='off_saved',output_accepted=job['output_accepted'],config_revision=revision))
            except (OSError,ValueError) as error:
                if job['kind']=='off':
                    result=dict(outcome='off_not_saved',output_accepted=job['output_accepted'])
                elif job['kind']=='command':
                    result=dict(outcome='command_superseded' if job['cancelled'].is_set() else 'command_not_saved',
                                persisted=persisted)
                elif job['cancelled'].is_set() or isinstance(error,SaveSuperseded):
                    result=dict(outcome='save_superseded',persisted=persisted)
                else:
                    result=dict(outcome='save_failed',message_key='settings_changed' if isinstance(error,ValueError) else 'storage_unavailable')
            reply=dict(result,session_id=key[0],request_id=key[1])
            if job['kind']=='command':
                self._command_recent[key]=(job['payload'],deepcopy(reply))
                while len(self._command_recent)>128:self._command_recent.popitem(last=False)
            replies.append(reply)
        # Never issue a clean-shutdown receipt while a worker is unfinished or
        # a late/stale durable write disagrees with the latest owner intent.
        # A successful Retry saving/Off or a fresh validated Save can reconcile
        # this; otherwise the existing open receipt forces neutral recovery.
        persisted=self.config.get('intent_v2')
        aligned=isinstance(persisted,dict) and persisted.get('mode')==self.owner.state.mode
        if aligned and self.owner.state.mode=='smart':
            aligned=self.config.get('smart_settings_v2')==self.owner.state.settings.to_dict()
        if aligned and self.owner.state.mode=='manual':
            aligned=persisted.get('manual')==asdict(self.owner.state.manual)
        if aligned:
            raw=self.config.get('override_v2')
            try:
                restored=(self.owner._restore_override(raw,self.owner.last_sample) if raw is not None else None)
                current=self.owner.state.override
                aligned=(restored is current if restored is None or current is None else
                         restored.kind==current.kind and restored.appearance==current.appearance and
                         abs(restored.expires_elapsed-current.expires_elapsed)<=1e-5)
            except (ValueError,TypeError,AttributeError,OverflowError):
                aligned=False
        self.config.owner_commit_pending=bool(self._jobs) or not aligned
        return replies

    def close(self, *, wait=True):
        self._assert_owner()
        if not self._closed:
            self._closed=True
            self._unsubscribe()
            self._worker.shutdown(wait=wait)
