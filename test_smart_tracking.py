"""Moving-reference tracking invariants, independent of real clocks/display."""
import math
import pytest
from smart_transition import ChannelTracker, ChannelTransition, LimitPolicy, MotionSample


def constant(value):return lambda t:MotionSample(value,0.,0.)


def assert_step(before,after,dt):
    assert 0<=after.position<=1
    assert abs(after.velocity)<=after.policy.rate+1e-12
    assert abs(after.velocity-before.velocity)<=after.policy.acceleration*dt+1e-12
    assert abs(after.position-before.position)<=after.policy.rate*dt+1e-12
    assert after.viable()


@pytest.mark.parametrize('hz',[5,10,20])
def test_constant_catchup_converges_without_restarting_an_ease(hz):
    tracker=ChannelTracker(0,0,LimitPolicy.channel('warmth',catch_up=True))
    dt=1/hz
    for _ in range(1500*hz):
        next_tracker=tracker.advance(constant(.6),dt)
        assert_step(tracker,next_tracker,dt)
        tracker=next_tracker
    assert tracker.position==pytest.approx(.6,abs=1e-6)
    assert abs(tracker.velocity)<1e-8


def test_tracks_morning_reference_not_saved_deep_night_peak():
    policy=LimitPolicy.channel('warmth')
    morning=ChannelTransition(.5,0,policy,preferred_seconds=7200)
    tracker=ChannelTracker(.8,0,LimitPolicy.channel('warmth',catch_up=True))
    for i in range(7500):
        updated=tracker.advance(lambda t:morning.sample(i+t),1.)
        assert_step(tracker,updated,1.)
        tracker=updated
    assert tracker.position<1e-5


def test_target_reversal_preserves_position_velocity_and_bounds():
    policy=LimitPolicy.channel('warmth',catch_up=True)
    tracker=ChannelTracker(.5,policy.rate,policy)
    assert tracker.viable()
    first=tracker.advance(constant(0),.1)
    assert first.velocity>0  # Brakes; never teleports velocity to its new sign.
    assert_step(tracker,first,.1)
    for _ in range(20000):
        following=first.advance(constant(0),.1)
        assert_step(first,following,.1)
        first=following
    assert first.position<1e-6


@pytest.mark.parametrize('edge',[0.,1.])
def test_boundary_braking_remains_feasible(edge):
    policy=LimitPolicy.channel('warmth',catch_up=True)
    speed=policy.rate/20
    distance=speed*speed/(2*policy.acceleration)
    start=distance if edge==0 else 1-distance
    velocity=-speed if edge==0 else speed
    tracker=ChannelTracker(start,velocity,policy)
    for _ in range(100):
        next_tracker=tracker.advance(constant(edge),.1)
        assert_step(tracker,next_tracker,.1)
        tracker=next_tracker


def test_late_callback_rebases_without_catching_up_all_elapsed_output():
    policy=LimitPolicy.channel('warmth',catch_up=True)
    tracker=ChannelTracker(.2,policy.rate/2,policy)
    rebased=tracker.advance(constant(.8),40.)
    assert rebased.position==tracker.position and rebased.velocity==0
    assert tracker.velocity==policy.rate/2  # Proposals do not mutate accepted state.


def test_invalid_reference_cannot_mutate_accepted_state():
    tracker=ChannelTracker(.2,0,LimitPolicy.channel('warmth'))
    with pytest.raises(ValueError):tracker.advance(constant(float('nan')),.1)
    assert tracker.position==.2
    with pytest.raises(ValueError):ChannelTracker(.999,.1,LimitPolicy(.1,.01))


@pytest.mark.parametrize('channel',['warmth','dim'])
@pytest.mark.parametrize('slower',[.5,1.])
def test_independent_channel_policies_and_slower_option(channel,slower):
    policy=LimitPolicy.channel(channel,catch_up=True,slower=slower)
    tracker=ChannelTracker(.1,0,policy)
    duration=math.ceil(.2/policy.rate+600)
    for _ in range(duration*5):
        next_tracker=tracker.advance(constant(.3),.2)
        assert_step(tracker,next_tracker,.2)
        tracker=next_tracker
    assert tracker.position==pytest.approx(.3,abs=1e-6)


def test_seeded_target_changes_keep_a_viable_braking_envelope():
    import random
    rng=random.Random(427)
    tracker=ChannelTracker(.999,0,LimitPolicy.channel('warmth',catch_up=True))
    target=0.
    for i in range(5000):
        if i%21==0:target=rng.choice([0.,1.,rng.random()])
        dt=rng.choice([.05,.1,.2,.7])
        next_tracker=tracker.advance(constant(target),dt)
        assert_step(tracker,next_tracker,dt)
        tracker=next_tracker
