"""GUI-polled migration handoff. Disk work never calls display or GUI APIs."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from smart_migration import commit_migration, uses_v2


class MigrationSwitch:
    def __init__(self, config, engine, proposal, binary_path, adopt, *, commit=commit_migration):
        self.config=config
        self.engine=engine
        self.adopt=adopt
        self.cancelled=Event()
        self.off_future=None
        self.done=False
        self.result=None
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='night-light-migration')
        self.previous_pending=config.owner_commit_pending
        config.owner_commit_pending=True
        def guard():
            if self.cancelled.is_set():raise RuntimeError('Migration superseded by Off.')
        self.future=self.executor.submit(commit,config,proposal,previewed=True,
                                         binary_path=binary_path,before_commit=guard)

    def off(self):
        """Neutral first; serialize durable Off after any racing migration commit."""
        if self.done:raise RuntimeError('Migration handoff already finished.')
        self.cancelled.set()
        self.engine.reset_to_neutral()
        if self.off_future is None:
            # Compute the patch on the worker, after the first job, so a v2
            # commit that raced cancellation cannot leave v2 Smart persisted.
            self.off_future=self.executor.submit(
                lambda:self.config.transactional_update_isolated(self.config.off_patch()))

    def poll(self):
        if self.done:return self.result
        if not self.future.done() or (self.off_future is not None and not self.off_future.done()):return None
        committed=False
        try:
            self.future.result()
            committed=True
        except Exception:
            # Do not export storage exception text or private file paths to UI.
            pass
        try:
            if self.off_future is not None:self.off_future.result()
        except Exception:
            self.engine.reset_to_neutral()
            self.result={'outcome':'migration_off_not_saved','adopted':False}
            self.done=True
            self.executor.shutdown(wait=False)
            return self.result  # Recovery receipt must remain open.
        if committed or uses_v2(self.config):
            try:
                self.config.owner_commit_pending=self.previous_pending
                self.adopt()
            except Exception:
                self.engine.reset_to_neutral()
                self.config.owner_commit_pending=True
                self.result={'outcome':'migration_activation_failed','adopted':False}
                self.done=True
                self.executor.shutdown(wait=False)
                return self.result  # No legacy scheduling may resume on v2 data.
        else:self.config.owner_commit_pending=self.previous_pending
        self.result={'outcome':('migration_off' if self.cancelled.is_set() else
                                'migrated' if committed else 'migration_failed'),
                     'adopted':uses_v2(self.config)}
        self.done=True
        self.executor.shutdown(wait=False)
        return self.result

    def close(self):
        """Leave recovery open; never adopt after the desktop closes."""
        if not self.done:
            self.off()
            self.executor.shutdown(wait=False)
