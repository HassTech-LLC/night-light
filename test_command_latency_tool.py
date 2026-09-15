"""The measurement tool's only real logic is its percentile, so pin that."""
import pytest

from tools.measure_command_latency import percentile


def test_nearest_rank_percentile_matches_hand_computed_values():
    values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    assert percentile(values, 0.95) == 100.0
    assert percentile(values, 0.5) == 50.0
    assert percentile(values, 0.1) == 10.0


def test_percentile_is_order_independent():
    assert percentile([3.0, 1.0, 2.0], 0.5) == 2.0


def test_p95_of_ten_samples_is_the_largest_sample():
    """Ten samples cannot resolve a true p95, so the reported figure is the max.

    Reports built from this tool must not present p95 as if it were estimated
    from a distribution large enough to support the claim.
    """
    values = [float(n) for n in range(1, 11)]
    assert percentile(values, 0.95) == max(values)


def test_single_sample_is_its_own_percentile():
    assert percentile([42.0], 0.95) == 42.0


def test_empty_samples_are_rejected():
    with pytest.raises(ValueError):
        percentile([], 0.95)
