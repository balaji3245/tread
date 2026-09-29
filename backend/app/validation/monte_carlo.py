import random
import statistics
from typing import List, Optional

from app.validation.validation_models import MonteCarloDistribution, MonteCarloResult


def _percentile(data: List[float], p: float) -> float:
    """Calculate the p-th percentile (0 <= p <= 100) of a sorted list."""
    if not data:
        return 0.0
    k = (len(data) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(data) - 1)
    d = k - f
    return round(data[f] + d * (data[c] - data[f]), 2)


def run_monte_carlo(
    r_multiples: List[float],
    initial_capital: float = 10000.0,
    risk_per_trade_usd: float = 100.0,
    simulations: int = 5000,
    random_seed: Optional[int] = 42
) -> MonteCarloResult:
    """
    Perform Monte Carlo trade-order sensitivity analysis via bootstrap resampling with replacement.
    Evaluates historical drawdown and sequence risk distributions over a specified simulation count.
    """
    if not r_multiples or simulations <= 0:
        empty_dist = MonteCarloDistribution(
            percentile_5=0.0,
            percentile_25=0.0,
            median=0.0,
            percentile_75=0.0,
            percentile_95=0.0
        )
        return MonteCarloResult(
            simulations=max(0, simulations),
            random_seed=random_seed,
            median_max_drawdown_usd=0.0,
            percentile_95_max_drawdown_usd=0.0,
            median_ending_r=0.0,
            percentile_5_ending_r=0.0,
            percentile_95_ending_r=0.0,
            max_observed_drawdown_usd=0.0,
            max_observed_losing_streak=0,
            drawdown_distribution=empty_dist,
            ending_r_distribution=empty_dist
        )

    rng = random.Random(random_seed)
    n_trades = len(r_multiples)

    max_drawdowns: List[float] = []
    ending_rs: List[float] = []
    max_losing_streaks: List[int] = []

    for _ in range(simulations):
        # Bootstrap sample with replacement
        sample_r = [rng.choice(r_multiples) for _ in range(n_trades)]

        # Simulate equity curve & drawdown
        equity = initial_capital
        peak = initial_capital
        sim_max_dd = 0.0
        cur_loss_streak = 0
        sim_max_loss_streak = 0

        for r in sample_r:
            equity += (r * risk_per_trade_usd)
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > sim_max_dd:
                sim_max_dd = dd

            if r < 0:
                cur_loss_streak += 1
                if cur_loss_streak > sim_max_loss_streak:
                    sim_max_loss_streak = cur_loss_streak
            else:
                cur_loss_streak = 0

        max_drawdowns.append(sim_max_dd)
        ending_rs.append(sum(sample_r))
        max_losing_streaks.append(sim_max_loss_streak)

    # Sort distributions for percentile calculation
    max_drawdowns.sort()
    ending_rs.sort()

    dd_dist = MonteCarloDistribution(
        percentile_5=_percentile(max_drawdowns, 5),
        percentile_25=_percentile(max_drawdowns, 25),
        median=_percentile(max_drawdowns, 50),
        percentile_75=_percentile(max_drawdowns, 75),
        percentile_95=_percentile(max_drawdowns, 95)
    )

    r_dist = MonteCarloDistribution(
        percentile_5=_percentile(ending_rs, 5),
        percentile_25=_percentile(ending_rs, 25),
        median=_percentile(ending_rs, 50),
        percentile_75=_percentile(ending_rs, 75),
        percentile_95=_percentile(ending_rs, 95)
    )

    return MonteCarloResult(
        simulations=simulations,
        random_seed=random_seed,
        median_max_drawdown_usd=dd_dist.median,
        percentile_95_max_drawdown_usd=dd_dist.percentile_95,
        median_ending_r=r_dist.median,
        percentile_5_ending_r=r_dist.percentile_5,
        percentile_95_ending_r=r_dist.percentile_95,
        max_observed_drawdown_usd=round(max(max_drawdowns), 2),
        max_observed_losing_streak=max(max_losing_streaks) if max_losing_streaks else 0,
        drawdown_distribution=dd_dist,
        ending_r_distribution=r_dist
    )
