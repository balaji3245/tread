import csv
import io
from typing import Any, Dict, List

from app.validation.validation_models import ValidationResponse


def export_validation_to_csv_dict(val_resp: ValidationResponse) -> Dict[str, str]:
    """
    Generate clean CSV formatted strings for all validation breakdowns.
    Returns a dictionary of filename -> CSV content string.
    """
    csv_files: Dict[str, str] = {}

    # 1. historical_data_summary.csv
    ds_buffer = io.StringIO()
    ds_writer = csv.writer(ds_buffer)
    ds_writer.writerow(["Metric", "Value"])
    ds_cov = val_resp.dataset_coverage
    dq = val_resp.data_quality
    ds_writer.writerow(["Symbol", ds_cov.source + " - " + val_resp.symbol])
    ds_writer.writerow(["Requested Start", ds_cov.requested_start_iso])
    ds_writer.writerow(["Requested End", ds_cov.requested_end_iso])
    ds_writer.writerow(["Actual Start", ds_cov.actual_start_iso])
    ds_writer.writerow(["Actual End", ds_cov.actual_end_iso])
    ds_writer.writerow(["Requested Days", ds_cov.requested_days])
    ds_writer.writerow(["Available Days", ds_cov.available_days])
    ds_writer.writerow(["1m Candle Count", ds_cov.candle_count_1m])
    ds_writer.writerow(["5m Candle Count", ds_cov.candle_count_5m])
    ds_writer.writerow(["Data Complete", "YES" if ds_cov.data_complete else "NO"])
    ds_writer.writerow(["Coverage Status", ds_cov.coverage_status])
    ds_writer.writerow(["Dataset Hash", ds_cov.dataset_hash])
    ds_writer.writerow(["Duplicate Timestamps", dq.duplicate_count_1m + dq.duplicate_count_5m])
    ds_writer.writerow(["Invalid OHLC Candles", dq.invalid_candles_count_1m + dq.invalid_candles_count_5m])
    ds_writer.writerow(["Non-monotonic Timestamps", dq.non_monotonic_count_1m + dq.non_monotonic_count_5m])
    ds_writer.writerow(["1m/5m Alignment", dq.alignment_status])
    ds_writer.writerow(["Timezone Normalization", dq.timezone])
    ds_writer.writerow(["Quality Status", "PASS" if dq.is_clean else "WARN"])
    csv_files["historical_data_summary.csv"] = ds_buffer.getvalue()

    # 2. walk_forward_results.csv
    wf_buffer = io.StringIO()
    wf_writer = csv.writer(wf_buffer)
    wf_writer.writerow([
        "Window", "Is Final OOS", "Train Start", "Train End", "Train Trades", "Train Win Rate %", "Train Total R", "Train Avg R", "Train Profit Factor", "Train Max DD ($)",
        "OOS Start", "OOS End", "OOS Trades", "OOS Win Rate %", "OOS Total R", "OOS Avg R", "OOS Profit Factor", "OOS Max DD ($)"
    ])
    for w in val_resp.walk_forward:
        tm = w.train_metrics
        vm = w.validation_metrics
        wf_writer.writerow([
            w.window_index,
            "YES" if w.is_final_oos else "NO",
            w.train_start_iso, w.train_end_iso, tm.trades_count, tm.win_rate, tm.total_r, tm.average_r, tm.profit_factor or "N/A", tm.max_drawdown_usd,
            w.validation_start_iso, w.validation_end_iso, vm.trades_count, vm.win_rate, vm.total_r, vm.average_r, vm.profit_factor or "N/A", vm.max_drawdown_usd
        ])
    csv_files["walk_forward_results.csv"] = wf_buffer.getvalue()

    # 3. oos_results.csv (Individual OOS Windows & Aggregates)
    oos_buffer = io.StringIO()
    oos_writer = csv.writer(oos_buffer)
    oos_writer.writerow([
        "OOS Window", "OOS Start", "OOS End", "Trades", "Winning", "Losing", "Win Rate %", "Total R", "Average R", "Profit Factor", "Max Drawdown ($)", "Long Trades", "Short Trades", "Is Final Locked OOS"
    ])
    for w in val_resp.walk_forward:
        vm = w.validation_metrics
        oos_writer.writerow([
            f"Window #{w.window_index}",
            w.validation_start_iso,
            w.validation_end_iso,
            vm.trades_count,
            vm.winning_trades,
            vm.losing_trades,
            vm.win_rate,
            vm.total_r,
            vm.average_r,
            vm.profit_factor or "N/A",
            vm.max_drawdown_usd,
            vm.long_trades,
            vm.short_trades,
            "YES" if w.is_final_oos else "NO"
        ])
    csv_files["oos_results.csv"] = oos_buffer.getvalue()

    # 4. monthly_results.csv
    m_buffer = io.StringIO()
    m_writer = csv.writer(m_buffer)
    m_writer.writerow([
        "Year-Month", "Month Name", "Trades", "Winning", "Losing", "Win Rate %", "Total R", "Average R", "Profit Factor", "Max Drawdown ($)", "Long Trades", "Short Trades", "1m Candles", "5m Candles", "Completeness"
    ])
    for m in val_resp.monthly:
        m_writer.writerow([
            m.year_month, m.month_name, m.trades, m.winning_trades, m.losing_trades, m.win_rate, m.total_r, m.average_r, m.profit_factor or "N/A", m.max_drawdown_usd, m.long_trades, m.short_trades, m.candle_count_1m, m.candle_count_5m, m.data_completeness
        ])
    csv_files["monthly_results.csv"] = m_buffer.getvalue()

    # 5. spread_sensitivity.csv
    sp_buffer = io.StringIO()
    sp_writer = csv.writer(sp_buffer)
    sp_writer.writerow(["Assumed Spread ($)", "Trades", "Win Rate %", "Average R", "Total R", "Profit Factor", "Max Drawdown ($)"])
    for s in val_resp.spread_sensitivity:
        sp_writer.writerow([s.spread, s.trades, s.win_rate, s.average_r, s.total_r, s.profit_factor or "N/A", s.max_drawdown_usd])
    csv_files["spread_sensitivity.csv"] = sp_buffer.getvalue()

    # 6. threshold_sensitivity.csv (Development Period)
    th_buffer = io.StringIO()
    th_writer = csv.writer(th_buffer)
    th_writer.writerow(["Score Threshold (Development)", "Signals", "Trades", "Win Rate %", "Average R", "Total R", "Profit Factor", "Max Drawdown ($)", "Small Sample Warning", "Sample Note"])
    for t in val_resp.threshold_sensitivity_development:
        th_writer.writerow([t.threshold, t.signals, t.trades, t.win_rate, t.average_r, t.total_r, t.profit_factor or "N/A", t.max_drawdown_usd, t.sample_size_warning, t.sample_size_note or ""])
    csv_files["threshold_sensitivity.csv"] = th_buffer.getvalue()

    # 7. exit_sensitivity.csv (Development Period)
    ex_buffer = io.StringIO()
    ex_writer = csv.writer(ex_buffer)
    ex_writer.writerow(["Case ID", "Label (Development)", "SL ATR Multiplier", "TP1 ATR Multiplier", "TP2 ATR Multiplier", "Trades", "Win Rate %", "Average R", "Total R", "Profit Factor", "Max Drawdown ($)"])
    for e in val_resp.exit_sensitivity_development:
        ex_writer.writerow([e.case_id, e.label, e.sl_atr_multiplier, e.tp1_atr_multiplier, e.tp2_atr_multiplier, e.trades, e.win_rate, e.average_r, e.total_r, e.profit_factor or "N/A", e.max_drawdown_usd])
    csv_files["exit_sensitivity.csv"] = ex_buffer.getvalue()

    # 8. diagnostics.csv
    diag_buffer = io.StringIO()
    diag_writer = csv.writer(diag_buffer)
    diag_writer.writerow(["Code", "Severity", "Title", "Measured Evidence"])
    for d in val_resp.diagnostics:
        diag_writer.writerow([d.code, d.severity, d.title, d.measured_evidence])
    csv_files["diagnostics.csv"] = diag_buffer.getvalue()

    return csv_files

