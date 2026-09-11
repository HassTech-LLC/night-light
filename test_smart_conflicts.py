"""Fake Magnification API ownership/readback tests; no real display calls."""
import ctypes
from nightlight_engine import NightLightEngine, MAGCOLOREFFECT


def identity():return tuple(float(i==j) for i in range(5) for j in range(5))


class MatrixBackend:
    def __init__(self):
        self.matrix=identity()
        self.writes=[]
        self.read_ok=True
        self.write_ok=True
    def MagInitialize(self):return True
    def MagUninitialize(self):return True
    def MagGetFullscreenColorEffect(self,pointer):
        if not self.read_ok:return False
        output=ctypes.cast(pointer,ctypes.POINTER(MAGCOLOREFFECT)).contents
        for i in range(5):
            for j in range(5):output.transform[i][j]=self.matrix[i*5+j]
        return True
    def MagSetFullscreenColorEffect(self,pointer):
        effect=ctypes.cast(pointer,ctypes.POINTER(MAGCOLOREFFECT)).contents
        matrix=tuple(float(effect.transform[i][j]) for i in range(5) for j in range(5))
        self.writes.append(matrix)
        if self.write_ok:self.matrix=matrix
        return self.write_ok


def setup():
    engine=NightLightEngine()
    backend=MatrixBackend()
    engine._mag=backend;engine._mag_available=True;engine._mag_initialized=True
    engine._readback_supported=True
    return engine,backend


def test_readback_distinct_from_last_write_and_not_a_physical_measurement():
    engine,backend=setup()
    assert engine._apply_matrix(1,.8,.6)
    observation=engine.output_observation()
    assert observation['provenance']=='readback'
    assert observation['accepted_rgb']==[1,.8,.6]
    assert abs(observation['readback_rgb'][1]-.8)<1e-6
    assert observation['readback_at'] is not None and observation['current_confirmed']


def test_other_owner_blocks_first_write_and_emergency_cleanup():
    engine,backend=setup()
    foreign=list(identity());foreign[1]=.2
    backend.matrix=tuple(foreign)
    assert not engine._apply_matrix(1,.8,.6)
    assert engine.output_fault=='external_conflict'
    for _ in range(3):assert not engine.reset_to_neutral()
    assert not backend.writes and backend.matrix==tuple(foreign)


def test_external_change_cancels_generation_and_stops_all_further_writes():
    engine,backend=setup()
    assert engine._apply_matrix(1,.8,.6)
    generation=engine.begin_automatic()
    foreign=list(backend.matrix);foreign[24]=.8
    backend.matrix=tuple(foreign)
    engine.refresh_output_observation()
    assert engine._transition_id>generation
    assert not engine.apply_automatic_sample(2500,.7,.1,generation)
    assert not engine._apply_matrix(1,1,1)
    assert len(backend.writes)==1
    assert engine.output_observation()['readback_rgb'] is None
    assert engine.output_observation()['accepted_rgb']==[1,.8,.6]


def test_failed_read_latches_uncertainty_without_issuing_a_write():
    engine,backend=setup()
    backend.read_ok=False
    assert not engine._apply_matrix(1,.8,.6)
    assert engine.output_fault=='backend_error' and not backend.writes
    backend.read_ok=True
    assert not engine._apply_matrix(1,.8,.6)
    assert not backend.writes
    assert engine.retry_display()
    assert engine.output_fault is None and len(backend.writes)==1


def test_retry_never_overwrites_a_still_foreign_matrix():
    engine,backend=setup()
    foreign=list(identity());foreign[0]=.7
    backend.matrix=tuple(foreign)
    assert not engine.retry_display() and not backend.writes
    backend.matrix=identity()
    assert engine.retry_display() and backend.writes==[identity()]


def test_failed_write_does_not_replace_accepted_or_readback_with_target():
    engine,backend=setup()
    assert engine._apply_matrix(1,.8,.6)
    backend.write_ok=False
    assert not engine._apply_matrix(1,.7,.4)
    observed=engine.output_observation()
    assert observed['accepted_rgb']==[1,.8,.6]
    assert abs(observed['readback_rgb'][1]-.8)<1e-6
    assert observed['requested_rgb']==[1,.7,.4] and not observed['current_confirmed']


def test_nonfinite_readback_is_backend_error_not_valid_appearance():
    engine,backend=setup()
    foreign=list(identity());foreign[0]=float('nan');backend.matrix=tuple(foreign)
    assert not engine._apply_matrix(1,.8,.6)
    assert engine.output_fault=='backend_error' and not backend.writes


def test_display_status_does_not_claim_no_external_filter_when_off():
    from display_status import derive_display_status
    state=derive_display_status(app_enabled=False,brightness=1,windows_active=False,
                                backend_applied=False,output_fault='external_conflict')
    assert not state.hass_effective and 'another' in state.summary.lower()


def test_off_can_recover_failed_write_only_when_current_matrix_is_still_ours():
    engine,backend=setup()
    assert engine._apply_matrix(1,.8,.6)
    backend.write_ok=False
    assert not engine._apply_matrix(1,.7,.4)
    backend.write_ok=True
    assert engine.reset_to_neutral()
    assert backend.matrix==identity() and not engine.is_enabled


def test_off_after_backend_error_never_resets_a_new_foreign_owner():
    engine,backend=setup()
    assert engine._apply_matrix(1,.8,.6)
    backend.write_ok=False
    assert not engine._apply_matrix(1,.7,.4)
    backend.write_ok=True
    foreign=list(identity());foreign[1]=.4;backend.matrix=tuple(foreign)
    count=len(backend.writes)
    assert not engine.reset_to_neutral()
    assert len(backend.writes)==count and engine.output_fault=='external_conflict'


def test_write_ack_followed_by_failed_readback_is_not_current_confirmation():
    engine,backend=setup()
    write=backend.MagSetFullscreenColorEffect
    def lose_readback(pointer):
        result=write(pointer);backend.read_ok=False
        return result
    backend.MagSetFullscreenColorEffect=lose_readback
    assert not engine._apply_matrix(1,.8,.6)
    observation=engine.output_observation()
    assert observation['accepted_rgb']==[1,.8,.6]
    assert observation['provenance']=='write_ack'
    assert observation['readback_matrix'] is None and not observation['current_confirmed']
    assert engine.output_fault=='backend_error'


def test_success_return_with_mismatching_readback_is_not_reported_applied():
    engine,backend=setup()
    backend.MagSetFullscreenColorEffect=lambda pointer:True
    assert not engine._apply_matrix(1,.8,.6)
    observation=engine.output_observation()
    assert observation['accepted_rgb']==[1,.8,.6]
    assert observation['readback_rgb']==[1.,1.,1.]
    assert not observation['current_confirmed'] and engine.output_fault=='external_conflict'
