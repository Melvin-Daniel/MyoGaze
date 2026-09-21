"""Generate an HTML product report from session + decision logs."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def build_report(
    session_path: Path | None = None,
    decisions_path: Path | None = None,
    out_path: Path | None = None,
    title: str = "NeuroShift Product Report",
) -> Path:
    root = Path(__file__).resolve().parents[2]
    logs = root / "logs"
    session_path = Path(session_path) if session_path else logs / "session_mock_latest.json"
    decisions_path = (
        Path(decisions_path) if decisions_path else logs / "decisions_mock_latest.jsonl"
    )
    out_path = Path(out_path) if out_path else logs / "neuroshift_report.html"

    session = {}
    if session_path.exists():
        session = json.loads(session_path.read_text(encoding="utf-8"))
    decisions = _read_jsonl(decisions_path)

    acts = sum(1 for d in decisions if d.get("action") == "ACT")
    abstains = sum(1 for d in decisions if d.get("action") == "ABSTAIN")
    far = session.get("far_proxy", 0.0)

    rows_html = "\n".join(
        (
            "<tr>"
            f"<td>{d.get('ts', '')}</td>"
            f"<td><b>{d.get('action')}</b></td>"
            f"<td>{d.get('selected_label') or d.get('selected_device') or '-'}</td>"
            f"<td>{d.get('reason', '')}</td>"
            f"<td>{d.get('yaw', '')}</td>"
            f"<td>{d.get('emg', '')}</td>"
            "</tr>"
        )
        for d in decisions[-80:]
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #0f1419;
      --card: #1a222c;
      --text: #e8eef5;
      --muted: #93a4b5;
      --accent: #3dd6c6;
      --warn: #f0b429;
      --danger: #f07178;
    }}
    body {{
      margin: 0; font-family: "Segoe UI", system-ui, sans-serif;
      background: radial-gradient(1200px 600px at 10% -10%, #1b2a3a, var(--bg));
      color: var(--text);
    }}
    header {{
      padding: 32px 40px 12px;
      border-bottom: 1px solid #2a3542;
    }}
    h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0.02em; }}
    .sub {{ color: var(--muted); }}
    .principle {{
      display: inline-block; margin-top: 12px; padding: 8px 12px;
      border-left: 3px solid var(--accent); background: #132028; color: #c9f7f0;
    }}
    main {{ padding: 24px 40px 48px; }}
    .grid {{
      display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr));
      gap: 14px; margin: 18px 0 28px;
    }}
    .stat {{
      background: var(--card); border: 1px solid #2b3644; border-radius: 10px;
      padding: 16px;
    }}
    .stat .k {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .stat .v {{ font-size: 28px; margin-top: 6px; font-weight: 650; }}
    table {{
      width: 100%; border-collapse: collapse; background: var(--card);
      border: 1px solid #2b3644; border-radius: 10px; overflow: hidden;
    }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #24303c; font-size: 13px; }}
    th {{ color: var(--muted); font-weight: 600; background: #151c24; }}
    .ok {{ color: var(--accent); }}
    .bad {{ color: var(--danger); }}
    footer {{ padding: 0 40px 40px; color: var(--muted); font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <div class="sub">Generated {datetime.now().strftime("%Y-%m-%d %H:%M")} · offline product demo</div>
    <div class="principle">Looking selects. Muscle confirms. Unsure → Abstain.</div>
  </header>
  <main>
    <div class="grid">
      <div class="stat"><div class="k">ACT events</div><div class="v ok">{acts}</div></div>
      <div class="stat"><div class="k">ABSTAIN events</div><div class="v">{abstains}</div></div>
      <div class="stat"><div class="k">Toggles</div><div class="v">{session.get("actuations", 0)}</div></div>
      <div class="stat"><div class="k">FAR proxy</div><div class="v {"bad" if far > 0.15 else "ok"}">{far:.3f}</div></div>
    </div>
    <h2>Decision log</h2>
    <table>
      <thead>
        <tr><th>Time</th><th>Action</th><th>Device</th><th>Reason</th><th>Yaw</th><th>EMG</th></tr>
      </thead>
      <tbody>
        {rows_html or '<tr><td colspan="6">No decisions logged yet.</td></tr>'}
      </tbody>
    </table>
  </main>
  <footer>
    Session file: {session_path.name} · Decisions: {decisions_path.name}<br/>
    FAR proxy = EMG confirms without a stable gazed target (Phase-0 stand-in until labeled trials).
  </footer>
</body>
</html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path


def build_trials_report(
    *,
    trials,
    session: dict | None = None,
    out_path: Path | None = None,
    title: str = "MyoGaze Phase-I Session Report",
    dwell_required: bool = True,
    detect_mode: str = "objects",
    cued: dict | None = None,
    cued_rows: list | None = None,
) -> Path:
    """HTML evidence pack from TrialLog + session metrics (Control App)."""
    root = Path(__file__).resolve().parents[2]
    out_path = Path(out_path) if out_path else root / "logs" / "neuroshift_session_report.html"
    session = session or {}
    summary = trials.summary() if hasattr(trials, "summary") else {}
    rows = trials.to_dicts() if hasattr(trials, "to_dicts") else []

    acts = summary.get("acts", session.get("acts", 0))
    abstains = summary.get("abstains", session.get("abstains", 0))
    confirms = summary.get("confirms", 0)
    actuations = summary.get("actuations", session.get("actuations", 0))
    far = float(session.get("far_proxy", 0.0) or 0.0)
    mode_label = "Dwell-gated" if dwell_required else "Instant gaze"

    def _fmt_latency(value: object) -> str:
        if value is None:
            return "—"
        try:
            return f"{float(value):.2f}s"
        except (TypeError, ValueError):
            return "—"

    cued = cued or {}
    cued_rows = cued_rows or []
    cued_trials = int(cued.get("trials") or 0)
    accuracy = float(cued.get("accuracy") or 0.0)
    far_real = float(cued.get("false_activation_rate") or 0.0)
    miss_rate = float(cued.get("miss_rate") or 0.0)
    latency = (cued.get("latency_s") or {}).get("median")
    latency_txt = "—" if latency is None else f"{latency:.2f}s"
    by = cued.get("by_condition") or {}

    def _cond(name: str) -> str:
        block = by.get(name) or {}
        if not block:
            return ""
        acc = float(block.get("accuracy") or 0)
        wr = float(block.get("false_activation_rate") or 0)
        return (
            f"<div class='stat'><div class='k'>{name.replace('_', ' ')}</div>"
            f"<div class='v'>{int(block.get('hits', 0))}/{int(block.get('trials', 0))}</div>"
            f"<div class='k'>acc {acc:.0%} · FAR {wr:.0%}</div></div>"
        )

    cued_rows_html = "\n".join(
        (
            "<tr>"
            f"<td>{r.get('index', '')}</td>"
            f"<td>{r.get('cued_label') or r.get('cued_device_id') or '-'}</td>"
            f"<td>{r.get('selected_label') or r.get('selected_device_id') or '-'}</td>"
            f"<td><b>{r.get('outcome') or 'pending'}</b></td>"
            f"<td>{'dwell' if r.get('dwell_required') else 'instant'}</td>"
            f"<td>{r.get('detect_mode', '')}</td>"
            f"<td>{_fmt_latency(r.get('latency_s'))}</td>"
            "</tr>"
        )
        for r in cued_rows[-80:]
    )

    cued_section = ""
    if cued_trials:
        cued_section = f"""
    <h2>Cued accuracy (ground truth)</h2>
    <div class="grid">
      <div class="stat"><div class="k">Accuracy</div><div class="v {'ok' if accuracy >= 0.7 else 'bad'}">{accuracy:.0%}</div></div>
      <div class="stat"><div class="k">False activations</div><div class="v {'bad' if far_real > 0.15 else 'ok'}">{far_real:.0%}</div></div>
      <div class="stat"><div class="k">Miss rate</div><div class="v">{miss_rate:.0%}</div></div>
      <div class="stat"><div class="k">Median latency</div><div class="v">{latency_txt}</div></div>
      {_cond("dwell_gated")}
      {_cond("instant_gaze")}
    </div>
    <table>
      <thead>
        <tr><th>#</th><th>Cued</th><th>Actuated</th><th>Outcome</th><th>Mode</th><th>Detect</th><th>Latency</th></tr>
      </thead>
      <tbody>
        {cued_rows_html or '<tr><td colspan="7">No cued trials scored.</td></tr>'}
      </tbody>
    </table>
"""

    rows_html = "\n".join(
        (
            "<tr>"
            f"<td>{r.get('trial_id', '')}</td>"
            f"<td>{r.get('ts', '')}</td>"
            f"<td>{r.get('event', '')}</td>"
            f"<td><b>{r.get('action', '')}</b></td>"
            f"<td>{r.get('label') or r.get('device_id') or '-'}</td>"
            f"<td>{'dwell' if r.get('dwell_required') else 'instant'}</td>"
            f"<td>{r.get('reason', '')}</td>"
            f"<td>{r.get('note', '')}</td>"
            "</tr>"
        )
        for r in rows[-120:]
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    body {{ margin: 0; font-family: Inter, "Segoe UI", system-ui, sans-serif;
      background: #f4f5f3; color: #12181a; }}
    header {{ padding: 28px 36px 16px; background: #fff; border-bottom: 1px solid #dde1dd; }}
    h1 {{ margin: 0 0 6px; font-size: 24px; }}
    .sub {{ color: #5b6660; font-size: 14px; }}
    .principle {{ margin-top: 12px; padding: 10px 12px; border-left: 3px solid #1f5c57;
      background: #e2ece9; color: #163f3c; display: inline-block; }}
    main {{ padding: 24px 36px 48px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px; margin: 16px 0 24px; }}
    .stat {{ background: #fff; border: 1px solid #dde1dd; border-radius: 10px; padding: 14px; }}
    .stat .k {{ color: #5b6660; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; }}
    .stat .v {{ font-size: 26px; margin-top: 6px; font-weight: 650; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff;
      border: 1px solid #dde1dd; border-radius: 10px; overflow: hidden; }}
    th, td {{ padding: 9px 11px; text-align: left; border-bottom: 1px solid #eceeeb; font-size: 12px; }}
    th {{ color: #5b6660; background: #f8f9f7; font-weight: 600; }}
    .ok {{ color: #1e7a4e; }}
    .bad {{ color: #b3402f; }}
    footer {{ padding: 0 36px 36px; color: #8b948e; font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <div class="sub">Generated {datetime.now().strftime("%Y-%m-%d %H:%M")} · mode={mode_label} · detect={detect_mode}</div>
    <div class="principle">Looking selects. Muscle confirms. Unsure → Abstain.</div>
  </header>
  <main>
    <div class="grid">
      <div class="stat"><div class="k">ACT</div><div class="v ok">{acts}</div></div>
      <div class="stat"><div class="k">ABSTAIN</div><div class="v">{abstains}</div></div>
      <div class="stat"><div class="k">Confirms</div><div class="v">{confirms}</div></div>
      <div class="stat"><div class="k">Actuations</div><div class="v">{actuations}</div></div>
      <div class="stat"><div class="k">FAR proxy</div><div class="v {"bad" if far > 0.15 else "ok"}">{far:.3f}</div></div>
            <div class="stat"><div class="k">Trial records</div><div class="v">{summary.get("total_records", len(rows))}</div></div>
    </div>
    {cued_section}
    <h2>Trial log</h2>
    <table>
      <thead>
        <tr><th>#</th><th>Time</th><th>Event</th><th>Action</th><th>Target</th><th>Mode</th><th>Reason</th><th>Note</th></tr>
      </thead>
      <tbody>
        {rows_html or '<tr><td colspan="8">No trial records yet — run a camera session and press Confirm.</td></tr>'}
      </tbody>
    </table>
  </main>
  <footer>
    Phase-I evidence pack · Confirm button stands in for EMG until MyoWare arrives.<br/>
    Export matching CSV/JSON from Insights for your report appendix.
  </footer>
</body>
</html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path
