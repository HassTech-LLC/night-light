from types import SimpleNamespace

from nightlight_engine import NightLightEngine


def fake_engine():
    engine=NightLightEngine()
    engine._mag_available=True
    engine._mag_initialized=True
    engine._mag=SimpleNamespace(MagInitialize=lambda:True,MagUninitialize=lambda:True,
                                MagSetFullscreenColorEffect=lambda matrix:True)
    return engine


def test_failed_write_preserves_last_accepted_observation():
    engine=fake_engine()
    assert engine._apply_matrix(1,.8,.6)
    previous=engine.output_observation()['accepted_rgb']
    engine._mag.MagSetFullscreenColorEffect=lambda matrix:False
    assert not engine._apply_matrix(1,.7,.4)
    observation=engine.output_observation()
    assert observation['accepted_rgb']==previous
    assert observation['requested_rgb']==[1,.7,.4]
    assert observation['error']
    assert observation['readback_rgb'] is None


def test_failed_neutral_does_not_claim_identity_was_accepted():
    engine=fake_engine()
    engine._apply_matrix(1,.8,.6)
    engine._mag.MagSetFullscreenColorEffect=lambda matrix:False
    assert engine.reset_to_neutral() is False
    assert not engine.is_enabled
    assert engine.output_observation()['accepted_rgb']==[1,.8,.6]
    assert engine.output_observation()['error']


def test_reinitialization_failure_does_not_write():
    engine=fake_engine()
    engine._mag_initialized=False
    engine._mag.MagInitialize=lambda:False
    calls=[]
    engine._mag.MagSetFullscreenColorEffect=lambda matrix:calls.append(matrix)
    assert engine._apply_matrix(1,.8,.6) is False
    assert not calls


def test_failed_command_does_not_call_success_callback():
    engine=fake_engine()
    engine._mag.MagSetFullscreenColorEffect=lambda matrix:False
    calls=[]
    engine.set_state(enabled=True,smooth=False,on_complete=lambda:calls.append('accepted'))
    assert not calls


def test_automatic_output_is_bounded_and_stale_samples_cannot_undo_off():
    engine=fake_engine()
    engine._apply_matrix(1,1,1)
    generation=engine.begin_automatic()
    assert engine.apply_automatic_sample(2500,.5,.1,generation)
    accepted=engine.output_observation()['accepted_rgb']
    assert all(1-value<=1/1024 for value in accepted)
    engine.reset_to_neutral()
    assert not engine.apply_automatic_sample(2500,.5,.1,generation)
    assert not engine.is_enabled


def test_automatic_unknown_start_and_windows_block_do_not_write():
    engine=fake_engine()
    generation=engine.begin_automatic()
    assert not engine.apply_automatic_sample(2500,.5,.1,generation)
    engine._apply_matrix(1,1,1)
    engine.set_windows_nightlight_policy(True)
    calls=[]
    engine._mag.MagSetFullscreenColorEffect=lambda matrix:calls.append(matrix)
    assert not engine.apply_automatic_sample(2500,.5,.1,generation)
    assert not calls


def test_automatic_gap_and_steady_state_skip_writes():
    engine=fake_engine()
    engine._apply_matrix(1,1,1)
    generation=engine.begin_automatic()
    calls=[]
    engine._mag.MagSetFullscreenColorEffect=lambda matrix:calls.append(matrix)
    assert engine.apply_automatic_sample(2500,.5,30,generation)
    assert engine.apply_automatic_sample(6500,1,.1,generation)
    assert not calls


def test_automatic_near_neutral_uses_continuous_mapping():
    from smart_transition import automatic_rgb
    engine=fake_engine()
    engine._apply_matrix(1,1,1)
    generation=engine.begin_automatic()
    assert engine.apply_automatic_sample(6499.99,1,.1,generation)
    assert engine.output_observation()['accepted_rgb']==list(automatic_rgb(6499.99,1))
    assert engine.apply_automatic_sample(6500,1,.1,generation)
    assert engine.output_observation()['accepted_rgb']==[1.,1.,1.]
