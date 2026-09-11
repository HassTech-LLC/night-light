import math
import pytest

from smart_transition import ChannelTransition, LimitPolicy, kelvin_to_warmth, warmth_to_kelvin, limit_rgb


@pytest.mark.parametrize('kelvin',[1200,2500,3500,4500,6500])
def test_warmth_coordinate_roundtrip(kelvin):
    assert warmth_to_kelvin(kelvin_to_warmth(kelvin))==pytest.approx(kelvin)


@pytest.mark.parametrize('rate',[1/7200,1/10800,1/1200,1/1800])
def test_planned_curve_obeys_rate_acceleration_and_endpoint(rate):
    policy=LimitPolicy(rate,rate/30)
    plan=ChannelTransition(0,1,policy,preferred_seconds=60)
    assert plan.sample(0).position==0
    assert plan.sample(plan.duration).position==pytest.approx(1)
    assert plan.sample(plan.duration).velocity==pytest.approx(0)
    samples=[plan.sample(plan.duration*i/1000) for i in range(1001)]
    assert all(0<=s.position<=1 for s in samples)
    assert max(abs(s.velocity) for s in samples)<=rate*(1+1e-10)
    assert max(abs(s.acceleration) for s in samples)<=policy.acceleration*(1+1e-10)


def test_replanning_preserves_position_velocity_and_brakes_without_jump():
    policy=LimitPolicy(1/1200,1/36000)
    first=ChannelTransition(0,.8,policy)
    previous=first.sample(first.duration*.4)
    revised=ChannelTransition(previous.position,.1,policy,velocity=previous.velocity)
    initial=revised.sample(0)
    assert initial.position==previous.position
    assert initial.velocity==previous.velocity
    samples=[revised.sample(revised.duration*i/1000) for i in range(1001)]
    assert max(abs(s.velocity) for s in samples)<=policy.rate*(1+1e-10)
    assert max(abs(s.acceleration) for s in samples)<=policy.acceleration*(1+1e-10)
    assert samples[-1].position==pytest.approx(.1)


def test_unreachable_braking_state_rejected_instead_of_clipped_jump():
    with pytest.raises(ValueError,match='braking'):
        ChannelTransition(.999,0,LimitPolicy(.1,.01),velocity=.1)


def test_rgb_limiter_rebases_long_gaps_and_skips_unchanged():
    before=(1.,1.,1.)
    assert limit_rgb(before,(.2,.3,.4),2)==before
    changed=limit_rgb(before,(.2,.3,.4),.1)
    assert all(abs(a-b)<=1/1024 for a,b in zip(before,changed))
    assert limit_rgb(changed,changed,.1)==changed


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),-1,2,True])
def test_invalid_normalized_target_rejected(bad):
    with pytest.raises(ValueError):ChannelTransition(0,bad,LimitPolicy(.01,.001))
