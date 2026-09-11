import pytest
from smart_transition import MotionSample, TrackingPair, forecast_handoff


def fixed(w,d):return lambda t:(MotionSample(w,0.,0.),MotionSample(d,0.,0.))


def test_handoff_requires_two_active_seconds_for_both_channels():
    pair=TrackingPair.start(0,0)
    almost=pair.advance(fixed(0,0),1.99)
    assert almost.catching_up
    done=almost.advance(fixed(0,0),.01)
    assert not done.catching_up
    assert done.warmth.position==0 and done.dim.position==0
    assert done.warmth.velocity==0 and done.dim.velocity==0
    only_warmth=pair.advance(fixed(0,.2),1.99)
    assert only_warmth.catching_up and only_warmth.matched_seconds==0


def test_gap_resets_handoff_window_without_spending_suspended_time():
    pair=TrackingPair.start(0,0).advance(fixed(0,0),1.9)
    gap=pair.advance(fixed(.5,.2),60)
    assert gap.matched_seconds==0 and gap.catching_up
    assert gap.warmth.position==0 and gap.dim.position==0
    assert gap.advance(fixed(0,0),.2).catching_up


def test_handoff_preserves_position_and_velocity_and_obeys_normal_ceiling():
    pair=TrackingPair.start(0,0)
    previous=pair
    for i in range(10000):
        pair=pair.advance(fixed(.15,.2),.1)
        if not pair.catching_up:break
        previous=pair
    else:pytest.fail('Catch-up never settled')
    for before,after in zip((previous.warmth,previous.dim),(pair.warmth,pair.dim)):
        assert abs(after.position-before.position)<=before.policy.rate*.1+1e-12
        assert abs(after.velocity-before.velocity)<=before.policy.acceleration*.1+1e-12
        assert abs(after.velocity)<=after.policy.rate
        assert after.viable()
    assert abs(pair.warmth.position-.15)<=1/1024
    assert abs(pair.dim.position-.2)<=1/1024


def test_rejoin_changes_ceiling_not_current_position_or_velocity():
    pair=TrackingPair.start(.1,.1,catching_up=False)
    moved=pair.advance(fixed(.15,.2),1)
    rejoined=moved.rejoin(fixed(.4,.4)(0))
    assert rejoined.catching_up
    assert rejoined.warmth.position==moved.warmth.position
    assert rejoined.warmth.velocity==moved.warmth.velocity


@pytest.mark.parametrize('hz',[5,10,20])
def test_forecast_matches_same_model_and_does_not_mutate_live_tracker(hz):
    pair=TrackingPair.start(0,0)
    predicted=forecast_handoff(pair,fixed(.15,.2),horizon=1800)
    assert predicted.reason=='estimated' and predicted.seconds is not None
    assert pair.warmth.position==0 and pair.catching_up
    live=pair;elapsed=0.
    while live.catching_up and elapsed<1800:
        live=live.advance(fixed(.15,.2),1/hz);elapsed+=1/hz
    assert abs(predicted.seconds-elapsed)<=1.1


def test_forecast_reports_uncertainty_and_cancellation_not_fake_arrival():
    pair=TrackingPair.start(0,0)
    assert forecast_handoff(pair,fixed(1,1),horizon=5).reason=='beyond_horizon'
    assert forecast_handoff(pair,fixed(1,1),cancelled=lambda:True).reason=='cancelled'
    assert forecast_handoff(pair,fixed(float('nan'),0)).reason=='reference_unavailable'


def test_forecast_uses_future_morning_path_not_constant_nightly_endpoint():
    from smart_transition import ChannelTransition,LimitPolicy
    morning=ChannelTransition(.3,0,LimitPolicy.channel('warmth'),preferred_seconds=4000)
    reference=lambda t:(morning.sample(1800+t),MotionSample(0,0,0))
    pair=TrackingPair.start(.6,0)
    predicted=forecast_handoff(pair,reference,horizon=3000)
    assert predicted.reason=='estimated'
    stationary=forecast_handoff(pair,fixed(morning.sample(1800).position,0),horizon=3000)
    assert abs(predicted.seconds-stationary.seconds)>10


def test_forecast_can_cancel_after_work_started_without_mutating_live_state():
    pair=TrackingPair.start(0,0);calls=[]
    def cancelled():
        calls.append(True)
        return len(calls)>=5
    result=forecast_handoff(pair,fixed(1,1),cancelled=cancelled)
    assert result.reason=='cancelled' and result.seconds is None
    assert 0<result.simulated_seconds<10
    assert pair.warmth.position==0 and pair.dim.position==0


@pytest.mark.parametrize('slower',[.5,1.])
def test_normal_handoff_keeps_each_slower_channel_policy(slower):
    from smart_transition import LimitPolicy
    pair=TrackingPair.start(0,0,slower=slower)
    pair=pair.advance(fixed(0,0),1)
    pair=pair.advance(fixed(0,0),1)
    assert not pair.catching_up
    assert pair.warmth.policy==LimitPolicy.channel('warmth',slower=slower)
    assert pair.dim.policy==LimitPolicy.channel('dim',slower=slower)
