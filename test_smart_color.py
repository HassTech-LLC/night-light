"""V2 transform continuity and the planner's RGB-rate feasibility contract."""
import pytest

from smart_transition import automatic_rgb, warmth_to_kelvin, LimitPolicy, RGB_STEP_PER_SECOND


def test_neutral_endpoint_has_no_jump():
    assert automatic_rgb(6500,1)==(1.,1.,1.)
    below=automatic_rgb(6500-1e-6,1)
    assert max(abs(1-v) for v in below)<1e-8


def test_mapping_is_monotone_bounded_and_continuous_in_warmth():
    previous=automatic_rgb(6500,1)
    # Includes the blue-floor crossing and both temperature endpoints.
    for i in range(1,10001):
        current=automatic_rgb(warmth_to_kelvin(i/10000),1)
        assert all(0<=v<=1 for v in current)
        assert all(b<=a+1e-12 for a,b in zip(previous,current))
        assert max(abs(a-b) for a,b in zip(previous,current))<=3/10000
        previous=current


@pytest.mark.parametrize('catch_up',[False,True])
@pytest.mark.parametrize('slower',[.5,1.])
def test_transform_derivative_bound_fits_policy(catch_up,slower):
    w=LimitPolicy.channel('warmth',catch_up=catch_up,slower=slower)
    d=LimitPolicy.channel('dim',catch_up=catch_up,slower=slower)
    # Analytic Lipschitz bound of the normalized logarithmic mapping.
    assert 3*w.rate+.8*d.rate<RGB_STEP_PER_SECOND


def test_dim_is_independent_and_neutral_warmth_can_still_dim():
    assert automatic_rgb(6500,.2)==pytest.approx((.2,.2,.2))
    full=automatic_rgb(2500,1)
    assert automatic_rgb(2500,.6)==pytest.approx(tuple(v*.6 for v in full))


@pytest.mark.parametrize('k,b',[(True,1),(float('nan'),1),(1199,1),(6501,1),(4000,True),(4000,.19)])
def test_invalid_transform_rejected(k,b):
    with pytest.raises(ValueError):automatic_rgb(k,b)


@pytest.mark.parametrize('ready,neutral',[('22:00','06:00'),('22:00','22:30')])
def test_extreme_scheduled_output_reaches_neutral_without_limiter_lag(ready,neutral):
    from datetime import date, timedelta, timezone
    from smart_schedule import personal_plan
    from smart_transition import limit_rgb
    plan=personal_plan(date(2026,9,9),timezone.utc,ready,neutral,kelvin=1200,dim_fraction=.8)
    start=min(plan.warmth.start,plan.dim.start)
    now=start
    accepted=(1.,1.,1.)
    # 1 Hz checks the complete dated trajectory. The analytic bound above
    # covers intermediate instants and the actual 5/10/20 Hz sampler rates.
    while now<plan.neutral:
        next_time=min(plan.neutral,now+timedelta(seconds=1))
        target=plan.sample(next_time)
        rgb=automatic_rgb(target.kelvin,target.brightness)
        accepted=limit_rgb(accepted,rgb,(next_time-now).total_seconds())
        assert accepted==pytest.approx(rgb,abs=1e-12)
        now=next_time
    assert accepted==pytest.approx((1.,1.,1.),abs=1e-12)
