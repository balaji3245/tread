import pytest
from app.validation.monte_carlo import run_monte_carlo


def test_monte_carlo_empty_dataset():
    res = run_monte_carlo(r_multiples=[], simulations=1000, random_seed=42)
    assert res.simulations == 1000
    assert res.median_ending_r == 0.0
    assert res.median_max_drawdown_usd == 0.0
    assert res.max_observed_losing_streak == 0


def test_monte_carlo_reproducibility():
    # Sample R multiples
    r_list = [1.0, -1.0, 1.5, -1.0, 2.0, -1.0, -1.0, 1.0, 1.2, -1.0, 2.5, -1.0]

    res1 = run_monte_carlo(r_multiples=r_list, simulations=2000, random_seed=42)
    res2 = run_monte_carlo(r_multiples=r_list, simulations=2000, random_seed=42)

    assert res1.median_max_drawdown_usd == res2.median_max_drawdown_usd
    assert res1.percentile_95_max_drawdown_usd == res2.percentile_95_max_drawdown_usd
    assert res1.median_ending_r == res2.median_ending_r
    assert res1.percentile_5_ending_r == res2.percentile_5_ending_r
    assert res1.percentile_95_ending_r == res2.percentile_95_ending_r
    assert res1.max_observed_drawdown_usd == res2.max_observed_drawdown_usd
    assert res1.max_observed_losing_streak == res2.max_observed_losing_streak


def test_monte_carlo_percentiles_order():
    r_list = [1.0, -1.0, 1.5, -1.0, 2.0, -1.0, -1.0, 1.0, 1.2, -1.0, 2.5, -1.0] * 5
    res = run_monte_carlo(r_multiples=r_list, simulations=1000, random_seed=123)

    dd_dist = res.drawdown_distribution
    assert dd_dist.percentile_5 <= dd_dist.percentile_25 <= dd_dist.median <= dd_dist.percentile_75 <= dd_dist.percentile_95

    r_dist = res.ending_r_distribution
    assert r_dist.percentile_5 <= r_dist.percentile_25 <= r_dist.median <= r_dist.percentile_75 <= r_dist.percentile_95
