#!/usr/bin/env python3
"""
Serve a local HTML crop-review page for a PR ingest batch.

Usage:
    python3 scripts/review_crops.py [--upstream-path PATH] [--output FILE] [--port N]

The page shows each cropped letter beside its metadata and an annotation form.
Feedback is auto-saved (via POST /feedback) to .review_feedback.json in the
repo root so Claude can read it back.
"""

from __future__ import annotations

import argparse
import base64
import http.server
import json
import os
import sys
import threading
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTRIES_PATH = REPO_ROOT / "data" / "index" / "entries.jsonl"
FEEDBACK_PATH = REPO_ROOT / ".review_feedback.json"

LETTER_DISPLAY_NAMES = {
    "alef": "Alef (א)", "bet": "Bet (ב)", "gimel": "Gimel (ג)",
    "dalet": "Dalet (ד)", "he": "He (ה)", "vav": "Vav (ו)",
    "zayin": "Zayin (ז)", "chet": "Chet (ח)", "tet": "Tet (ט)",
    "yod": "Yod (י)", "kaf": "Kaf (כ)", "lamed": "Lamed (ל)",
    "mem": "Mem (מ)", "nun": "Nun (נ)", "samech": "Samech (ס)",
    "ayin": "Ayin (ע)", "pe": "Pe (פ)", "tsadi": "Tsadi (צ)",
    "qof": "Qof (ק)", "resh": "Resh (ר)", "shin": "Shin (ש)",
    "tav": "Tav (ת)", "kaf_sofit": "Kaf sofit (ך)", "mem_sofit": "Mem sofit (ם)",
    "nun_sofit": "Nun sofit (ן)", "pe_sofit": "Pe sofit (ף)", "tsadi_sofit": "Tsadi sofit (ץ)",
}


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def _mime(path: Path) -> str:
    return "image/png" if path.suffix.lower() == ".png" else "image/jpeg"


def _load_entries() -> list[dict]:
    entries = []
    with ENTRIES_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _find_upstream_scan(entry: dict, upstream_root: Path | None) -> Path | None:
    if upstream_root is None:
        return None
    source_id = entry["upstream"]["source_id"]
    upstream_entry_id = entry["upstream"]["entry_id"]
    for ext in (".jpg", ".jpeg", ".png"):
        p = upstream_root / "data" / "scans" / source_id / f"{upstream_entry_id}{ext}"
        if p.exists():
            return p
    return None


def _build_html(entries: list[dict], upstream_root: Path | None) -> str:
    # Group entries by upstream scan so we render each scan once.
    from collections import defaultdict
    by_scan: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        by_scan[e["upstream"]["entry_id"]].append(e)

    scan_sections_html = ""
    for upstream_entry_id, scan_entries in by_scan.items():
        first = scan_entries[0]
        scan_path = _find_upstream_scan(first, upstream_root)

        if scan_path:
            scan_b64 = _b64(scan_path)
            scan_mime = _mime(scan_path)
            # Build bbox overlay objects for JS
            bboxes_json = json.dumps([
                {
                    "x": e["upstream"]["bbox"]["x"],
                    "y": e["upstream"]["bbox"]["y"],
                    "w": e["upstream"]["bbox"]["w"],
                    "h": e["upstream"]["bbox"]["h"],
                    "label": e["letter"]["name"],
                    "entry_id": e["entry_id"],
                }
                for e in scan_entries
            ])
            scan_section = f"""
<div class="scan-block">
  <h2>Upstream scan: <code>{upstream_entry_id}</code></h2>
  <div class="scan-container">
    <canvas id="canvas_{upstream_entry_id}"
            data-src="data:{scan_mime};base64,{scan_b64}"
            data-bboxes='{bboxes_json}'
            class="scan-canvas"></canvas>
  </div>
  <p class="hint">Bboxes are shown at 3× zoom. Click a bbox to jump to that letter's card below.</p>
</div>
"""
        else:
            scan_section = f"""
<div class="scan-block">
  <h2>Upstream scan: <code>{upstream_entry_id}</code></h2>
  <p class="warn">Upstream scan not found locally. Run with
  <code>--upstream-path /path/to/public-domain-hand-written-hebrew-scans</code>
  to display it.</p>
</div>
"""
        scan_sections_html += scan_section

    cards_html = ""
    for e in entries:
        entry_id = e["entry_id"]
        letter_name = e["letter"]["name"]
        display = LETTER_DISPLAY_NAMES.get(letter_name, letter_name)
        img_path = REPO_ROOT / e["image"]["local_path"]
        img_data = f"data:{_mime(img_path)};base64,{_b64(img_path)}" if img_path.exists() else ""
        bbox = e["upstream"]["bbox"]
        w_px = e["image"]["width_px"]
        h_px = e["image"]["height_px"]
        style = e["letter"].get("style", "")
        legibility = e["quality"]["legibility"]
        usable_htr = e["quality"]["usable_for_htr"]

        cards_html += f"""
<div class="card" id="card_{entry_id}" data-entry-id="{entry_id}">
  <div class="card-header">
    <span class="entry-id">{entry_id}</span>
    <span class="letter-name">{display}</span>
  </div>
  <div class="card-body">
    <div class="crop-view">
      {'<img src="' + img_data + '" alt="' + letter_name + '" class="crop-img">' if img_data else '<p class="warn">Image file not found.</p>'}
      <div class="crop-meta">
        <table>
          <tr><td>Size</td><td>{w_px}×{h_px} px</td></tr>
          <tr><td>Bbox (x,y,w,h)</td><td>{bbox['x']},{bbox['y']},{bbox['w']},{bbox['h']}</td></tr>
          <tr><td>Style</td><td>{style}</td></tr>
          <tr><td>Legibility</td><td>{legibility}</td></tr>
          <tr><td>HTR-usable</td><td>{'yes' if usable_htr else 'no'}</td></tr>
        </table>
      </div>
    </div>
    <div class="feedback-form">
      <div class="radio-group">
        <label><input type="radio" name="verdict_{entry_id}" value="correct"> Correct label</label>
        <label><input type="radio" name="verdict_{entry_id}" value="wrong"> Wrong label</label>
        <label><input type="radio" name="verdict_{entry_id}" value="uncertain"> Uncertain</label>
        <label><input type="radio" name="verdict_{entry_id}" value="drop"> Drop this entry</label>
      </div>
      <div class="relabel-row" id="relabel_{entry_id}" style="display:none">
        <label>Correct letter:
          <input type="text" id="relabel_text_{entry_id}" placeholder="e.g. ayin" size="16">
        </label>
      </div>
      <textarea id="notes_{entry_id}" placeholder="Free-text notes (optional)" rows="2"></textarea>
      <button class="save-btn" onclick="saveCard('{entry_id}')">Save feedback</button>
      <span class="saved-indicator" id="saved_{entry_id}"></span>
    </div>
  </div>
</div>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Crop Review</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 1100px; margin: 0 auto; padding: 1rem 2rem; background: #f8f8f8; }}
  h1 {{ font-size: 1.4rem; border-bottom: 2px solid #333; padding-bottom: .4rem; }}
  h2 {{ font-size: 1.1rem; color: #555; }}
  code {{ font-size: .85em; background: #eee; padding: 1px 4px; border-radius: 3px; }}
  .hint {{ color: #777; font-size: .85rem; margin: .3rem 0 1rem; }}
  .warn {{ color: #c00; font-size: .9rem; }}
  .scan-block {{ background: #fff; padding: 1rem; border-radius: 6px; margin-bottom: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,.1); }}
  .scan-container {{ overflow-x: auto; }}
  .scan-canvas {{ display: block; image-rendering: pixelated; cursor: crosshair; }}
  .card {{ background: #fff; border-radius: 6px; padding: 1rem; margin-bottom: 1.2rem; box-shadow: 0 1px 4px rgba(0,0,0,.1); }}
  .card.highlight {{ outline: 3px solid #3a7bd5; }}
  .card-header {{ display: flex; gap: 1rem; align-items: baseline; margin-bottom: .6rem; }}
  .entry-id {{ font-family: monospace; font-size: .85rem; color: #666; }}
  .letter-name {{ font-size: 1.1rem; font-weight: 600; }}
  .card-body {{ display: flex; gap: 1.5rem; flex-wrap: wrap; }}
  .crop-view {{ display: flex; gap: 1rem; align-items: flex-start; }}
  .crop-img {{ image-rendering: pixelated; width: auto; height: auto; min-width: 60px; max-width: 200px; border: 1px solid #ccc; background: #fff; }}
  .crop-meta table {{ border-collapse: collapse; font-size: .85rem; }}
  .crop-meta td {{ padding: 2px 8px 2px 0; vertical-align: top; }}
  .crop-meta td:first-child {{ color: #666; white-space: nowrap; }}
  .feedback-form {{ flex: 1; min-width: 260px; }}
  .radio-group {{ display: flex; flex-direction: column; gap: .3rem; font-size: .9rem; margin-bottom: .5rem; }}
  .relabel-row {{ margin-bottom: .5rem; font-size: .9rem; }}
  textarea {{ width: 100%; box-sizing: border-box; font-size: .85rem; resize: vertical; }}
  .save-btn {{ margin-top: .4rem; padding: .3rem .9rem; cursor: pointer; background: #3a7bd5; color: #fff; border: none; border-radius: 4px; font-size: .85rem; }}
  .save-btn:hover {{ background: #2a5baa; }}
  .saved-indicator {{ font-size: .8rem; color: green; margin-left: .5rem; }}
  #global-status {{ position: fixed; bottom: 1rem; right: 1.5rem; background: #222; color: #fff; padding: .4rem .9rem; border-radius: 4px; font-size: .85rem; display: none; z-index: 999; }}
</style>
</head>
<body>
<h1>Crop Review</h1>
<p>Review each cropped letter. Select a verdict, optionally add notes, then click <strong>Save feedback</strong>.
All feedback is written to <code>.review_feedback.json</code> at the repo root.</p>

{scan_sections_html}

<h2>Per-letter cards</h2>
{cards_html}

<div id="global-status"></div>

<script>
const ZOOM = 3;

// ---- canvas rendering ----
document.querySelectorAll('.scan-canvas').forEach(canvas => {{
  const img = new Image();
  img.onload = () => {{
    canvas.width = img.width * ZOOM;
    canvas.height = img.height * ZOOM;
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    const bboxes = JSON.parse(canvas.dataset.bboxes);
    bboxes.forEach(b => {{
      ctx.strokeStyle = '#ff3300';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(b.x * ZOOM, b.y * ZOOM, b.w * ZOOM, b.h * ZOOM);
      ctx.fillStyle = '#ff3300';
      ctx.font = `${{Math.max(10, ZOOM * 4)}}px monospace`;
      ctx.fillText(b.label, b.x * ZOOM, Math.max(b.y * ZOOM - 2, 10));
    }});
    canvas.addEventListener('click', e => {{
      const rect = canvas.getBoundingClientRect();
      const cx = (e.clientX - rect.left) / ZOOM;
      const cy = (e.clientY - rect.top) / ZOOM;
      const hit = bboxes.find(b => cx >= b.x && cx <= b.x + b.w && cy >= b.y && cy <= b.y + b.h);
      if (hit) jumpToCard(hit.entry_id);
    }});
  }};
  img.src = canvas.dataset.src;
}});

// ---- show/hide relabel input ----
document.querySelectorAll('input[type=radio]').forEach(r => {{
  r.addEventListener('change', () => {{
    const entryId = r.name.replace('verdict_', '');
    const relabel = document.getElementById('relabel_' + entryId);
    if (relabel) relabel.style.display = r.value === 'wrong' ? 'block' : 'none';
  }});
}});

// ---- jump to card ----
function jumpToCard(entryId) {{
  const card = document.getElementById('card_' + entryId);
  if (!card) return;
  document.querySelectorAll('.card').forEach(c => c.classList.remove('highlight'));
  card.classList.add('highlight');
  card.scrollIntoView({{behavior: 'smooth', block: 'center'}});
}}

// ---- feedback persistence ----
let feedback = {{}};

async function loadFeedback() {{
  try {{
    const r = await fetch('/feedback');
    if (r.ok) feedback = await r.json();
    restoreUI();
  }} catch(e) {{}}
}}

function restoreUI() {{
  Object.entries(feedback).forEach(([entryId, fb]) => {{
    const radio = document.querySelector(`input[name="verdict_${{entryId}}"][value="${{fb.verdict}}"]`);
    if (radio) {{
      radio.checked = true;
      radio.dispatchEvent(new Event('change'));
    }}
    if (fb.relabel) {{
      const rt = document.getElementById('relabel_text_' + entryId);
      if (rt) rt.value = fb.relabel;
    }}
    const notes = document.getElementById('notes_' + entryId);
    if (notes && fb.notes) notes.value = fb.notes;
    markSaved(entryId);
  }});
}}

async function saveCard(entryId) {{
  const verdict = document.querySelector(`input[name="verdict_${{entryId}}"]:checked`)?.value;
  const notes = document.getElementById('notes_' + entryId)?.value?.trim();
  const relabelEl = document.getElementById('relabel_text_' + entryId);
  const relabel = relabelEl?.value?.trim() || null;

  feedback[entryId] = {{ verdict: verdict || null, relabel, notes: notes || null }};
  try {{
    const r = await fetch('/feedback', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(feedback),
    }});
    if (r.ok) markSaved(entryId);
    else showStatus('Save failed: ' + r.status, true);
  }} catch(e) {{ showStatus('Save failed: ' + e.message, true); }}
}}

function markSaved(entryId) {{
  const el = document.getElementById('saved_' + entryId);
  if (el) {{ el.textContent = '✓ saved'; setTimeout(() => el.textContent = '', 3000); }}
}}

function showStatus(msg, err=false) {{
  const el = document.getElementById('global-status');
  el.textContent = msg;
  el.style.background = err ? '#c00' : '#222';
  el.style.display = 'block';
  setTimeout(() => el.style.display = 'none', 4000);
}}

loadFeedback();
</script>
</body>
</html>
"""


class _Handler(http.server.BaseHTTPRequestHandler):
    html: str = ""

    def log_message(self, fmt, *args):
        pass  # suppress request log noise

    def do_GET(self):
        if self.path == "/":
            body = self._html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/feedback":
            data = {}
            if FEEDBACK_PATH.exists():
                try:
                    data = json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    pass
            body = json.dumps(data, ensure_ascii=False, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/feedback":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode())
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                return
            FEEDBACK_PATH.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            self.send_response(204)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def main() -> None:
    ap = argparse.ArgumentParser(description="Serve a crop-review page locally.")
    ap.add_argument("--upstream-path", metavar="PATH",
                    help="Path to a clone of HeOCR/public-domain-hand-written-hebrew-scans")
    ap.add_argument("--output", metavar="FILE",
                    help="Write the HTML to this file instead of serving it")
    ap.add_argument("--port", type=int, default=8765,
                    help="Local port to serve on (default: 8765)")
    args = ap.parse_args()

    upstream_root = Path(args.upstream_path) if args.upstream_path else None
    entries = _load_entries()
    html = _build_html(entries, upstream_root)

    if args.output:
        Path(args.output).write_text(html, encoding="utf-8")
        print(f"Written to {args.output}")
        return

    # Patch the handler class with the rendered HTML.
    _Handler._html = html

    server = http.server.HTTPServer(("127.0.0.1", args.port), _Handler)
    url = f"http://localhost:{args.port}/"
    print(f"Review server running at {url}")
    print(f"Feedback will be saved to {FEEDBACK_PATH}")
    print("Press Ctrl+C to stop.")

    threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
