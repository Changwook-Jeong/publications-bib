"""Honest, separately scaled PI citation snapshot; never presented as live data."""
from __future__ import annotations

import html
import json
import math
from datetime import date
from pathlib import Path

SCHOLAR = "https://scholar.google.com/citations?user=CPYw1roAAAAJ&hl=en"


def load_snapshot(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("approximate") is not True:
        raise ValueError("Citation snapshot must identify its schema and approximate values")
    if data.get("source_url") != SCHOLAR:
        raise ValueError("Unexpected citation source")
    date.fromisoformat(data["provided_on"])
    if data.get("snapshot_date"):
        date.fromisoformat(data["snapshot_date"])
    values = data.get("annual_citations", {})
    if not values or any(not str(y).isdigit() or not isinstance(n, int) or isinstance(n, bool) or n < 0
                         for y, n in values.items()):
        raise ValueError("Invalid annual citation estimate")
    return data


def citation_plot(data: dict, start: int, end: int) -> str:
    # Only supplied observations are drawn. Missing years are not invented as zeros.
    rows = [(int(y), n) for y, n in data["annual_citations"].items() if start <= int(y) <= end]
    rows.sort()
    maximum = max((n for _, n in rows), default=0)
    ceiling = max(100, math.ceil(maximum / 100) * 100)
    baseline, top, left, width = 250, 20, 45, 440
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" class="citation-plot" viewBox="0 0 {width} 315" role="img" aria-labelledby="citation-chart-title citation-chart-desc">',
             '<title id="citation-chart-title">Approximate annual citations to the PI’s Google Scholar profile</title>',
             '<desc id="citation-chart-desc">Screenshot estimates, not exact values or a live feed. Profile-wide citations include earlier research. The 2026 bar is partial-year.</desc>']
    for value in range(0, ceiling + 1, 100):
        y = baseline - (baseline - top) * value / ceiling
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="425" y2="{y:.1f}" stroke="#e6edeb"/><text x="{left-10}" y="{y+4:.1f}" text-anchor="end" fill="#61757b" font-size="12">{value}</text>')
    column = 380 / max(1, len(rows))
    for i, (year, value) in enumerate(rows):
        x = left + (i + .5) * column
        height = (baseline - top) * value / ceiling
        partial = year == data.get("partial_year", 2026)
        parts.append(f'<g data-citation-year="{year}" data-citation-estimate="{value}"><title>{year}: approximately {value} citations{" (partial year)" if partial else ""}</title><rect x="{x-18:.1f}" y="{baseline-height:.1f}" width="36" height="{height:.1f}" rx="3" fill="#647c88"{" fill-opacity=\"0.65\"" if partial else ""}/><text x="{x:.1f}" y="{baseline-height-10:.1f}" text-anchor="middle" fill="#365460" font-size="13">~{value}</text><text x="{x:.1f}" y="278" text-anchor="middle" fill="#294a54" font-size="13">{year}{"*" if partial else ""}</text></g>')
    parts.append('</svg>')
    return ''.join(parts)


def citation_section(data: dict, start: int, end: int) -> str:
    rows = [(int(y), n) for y, n in data["annual_citations"].items() if start <= int(y) <= end]
    rows.sort()
    received = date.fromisoformat(data["provided_on"]).strftime('%d %b %Y')
    table = ''.join(f'<tr><th scope="row">{y}</th><td>~{n}</td></tr>' for y, n in rows)
    return f'''<aside class="citation-panel" aria-labelledby="citation-heading">
      <div><p class="eyebrow">GOOGLE SCHOLAR</p><h3 id="citation-heading">PI citation impact</h3></div>
      <figure>{citation_plot(data, start, end)}<figcaption>Approximate values · * Partial year</figcaption></figure>
      <details class="citation-source"><summary>Source &amp; details</summary>
      <p>* 2026 is partial-year in the supplied screenshot. Includes earlier academic and industrial work; not citations to UNIST-group papers alone.</p>
      <p>Estimated from a user-supplied Google Scholar screenshot, received {html.escape(received)}. Capture date was not recorded. Not live-synced.</p>
      <table><caption>Approximate annual citations shown in the chart</caption><thead><tr><th scope="col">Year</th><th scope="col">Citations</th></tr></thead><tbody>{table}</tbody></table></details>
      <a class="citation-source-link" href="{html.escape(data['source_url'], quote=True)}" target="_blank" rel="noopener">Google Scholar ↗</a>
    </aside>'''
