from typing import Any

from app.notifications.chunker import chunk_message


def _item_line(item: dict[str, Any]) -> str:
    metrics = item.get("metrics", {})
    f30, oi, ticker = metrics.get("30m", {}), metrics.get("oi", {}), metrics.get("ticker", {})
    return (
        f"#{item.get('rank','-')} {item.get('contract','-')} {item.get('direction','-')} | "
        f"score {item.get('ranking_score',0):.1f} bull {item.get('bull_score',0):.1f} "
        f"bear {item.get('bear_score',0):.1f} confidence {item.get('confidence',0):.1f}\n"
        f"4H {item.get('market_state','-')} | 30m {item.get('signal_state','-')} | "
        f"24h {ticker.get('change_percentage','unavailable')}% turnover {ticker.get('turnover_usdt','unavailable')} "
        f"ADX {f30.get('adx','unavailable')} +DI {f30.get('plus_di','unavailable')} "
        f"-DI {f30.get('minus_di','unavailable')} MFI {f30.get('mfi','unavailable')} "
        f"OI30m {oi.get('oi_change_30m_pct','unavailable')}%\n"
        f"原因: {', '.join(item.get('reasons',[])[:4]) or 'unavailable'} | "
        f"風險: {', '.join(item.get('risk_flags',[])[:6]) or 'none'}"
    )


def format_scan(result: dict[str, Any]) -> list[str]:
    lines = [
        f"Gate 掃描完成 {result.get('finished_at','')}",
        f"scan_id={result.get('scan_id')} universe={result.get('universe_total',0)} "
        f"success={result.get('successful_count',0)} errors={result.get('error_count',0)}",
        "把握程度不等於實際勝率。",
    ]
    for title, key in (("綜合排名", "combined"), ("做多排名", "long"), ("做空排名", "short")):
        lines.append(f"\n【{title}】")
        items = result.get("rankings", {}).get(key, [])
        lines.extend(_item_line(item) for item in items)
        if not items:
            lines.append("此類型無可靠排名")
    return chunk_message("\n".join(lines))


def format_replay_overview(job: dict[str, Any]) -> list[str]:
    diagnostics = job.get("diagnostics", {})
    return chunk_message(
        "\n".join(
            [
                "Gate 歷史重播完成",
                f"開始 {job.get('request',{}).get('start_time')} 結束 {job.get('request',{}).get('end_time')}",
                f"時間點 {len(job.get('results',[]))} 成功 {diagnostics.get('reliable_timepoints',0)} "
                f"無可靠排名 {diagnostics.get('unreliable_timepoints',0)}",
                f"API errors {diagnostics.get('api_errors',0)} indicator errors {diagnostics.get('indicator_errors',0)}",
                f"結果頁 {job.get('result_url','unavailable')}",
                "若時間點過多，此訊息為精簡版，完整資料請使用結果頁與匯出檔。",
            ]
        )
    )


def format_replay_timepoint(timepoint: dict[str, Any], include_all: bool) -> list[str]:
    lines = [f"{timepoint.get('aligned_time')} 綜合排名"]
    rankings = timepoint.get("rankings", {})
    for key in ("combined", "long", "short") if include_all else ("combined",):
        lines.append(f"【{key}】")
        lines.extend(_item_line(item) for item in rankings.get(key, []))
        if not rankings.get(key):
            lines.append("無可靠排名")
    return chunk_message("\n".join(lines))

