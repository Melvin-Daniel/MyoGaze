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
