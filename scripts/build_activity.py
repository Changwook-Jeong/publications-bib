"""Bibliography-derived statistics and a paired paper/patent history."""
from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from build_citations import citation_section

from build_publications import (
    citation_text, clean_tex, display_author, entry_category, entry_month,
    entry_year, parse_bibtex, render_authors, split_authors,
)

START_YEAR = 2007
ANNUAL_START_YEAR = 2022
LABELS = {"journals": "Journal article", "conferences": "Conference paper", "patents": "Patent record"}
JURISDICTIONS = {"KR": "Korea (KR)", "non-KR": "Outside Korea", "unknown": "Jurisdiction not recorded"}


def patent_jurisdiction(entry) -> str:
    """Jurisdiction is the patent office, never an inventor/assignee's nationality."""
    for field in ("number", "patentnumber", "url", "publisher", "country"):
        text = clean_tex(entry.fields.get(field, ""))
        if re.search(r"\bKR\s*\d|Korean Patent|Korea(?:n)?\b|대한민국|한국", text, re.I):
            return "KR"
        if re.search(r"\b(?:US|EP|WO|JP|CN|TW|GB|CA|AU|DE|FR|IN)\s*\d|U\.?S\.?\s+Patent|United States|European Patent|PCT", text, re.I):
            return "non-KR"
    return "unknown"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def public_link(entry, curated: dict) -> str:
    record = curated.get(entry.key, {})
    if slug := record.get("slug"):
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            return slug + "/"
    doi = record.get("doi") or clean_tex(entry.fields.get("doi", ""))
    if re.fullmatch(r"10\.\d{4,9}/[^\s<>\"']+", doi):
        return "https://doi.org/" + doi
    url = clean_tex(entry.fields.get("url", ""))
    parsed = urlsplit(url)
    if (parsed.scheme in {"http", "https"} and parsed.hostname
            and not parsed.username and not parsed.password
            and parsed.hostname not in {"localhost", "::1"}
            and not re.fullmatch(r"[\d.]+", parsed.hostname)):
        return url
    return ""


def load_activity(bib: Path, data: Path, as_of: date, start: int = START_YEAR) -> dict:
    source = json.loads(data.read_text(encoding="utf-8"))
    curated = {p["citation_key"]: p for p in source.get("papers", [])}
    exact_dates = source.get("publication_dates", {})
    groups = {"papers": [], "patents": []}
    for entry in parse_bibtex(bib.read_text(encoding="utf-8-sig")):
        category, year, month = entry_category(entry), entry_year(entry), entry_month(entry)
        if category not in LABELS or not start <= year <= as_of.year:
            continue
        if year == as_of.year and month > as_of.month:
            continue
        if exact := exact_dates.get(entry.key):
            parsed = date.fromisoformat(exact)
            if parsed.year == year and (not month or parsed.month == month) and parsed > as_of:
                continue
        row = dict(key=entry.key, id=hashlib.sha256(entry.key.encode()).hexdigest()[:14],
                   entry=entry, category=category, year=year, month=month,
                   title=clean_tex(entry.fields.get("title", "Untitled")),
                   url=public_link(entry, curated))
        if category == "patents":
            row["jurisdiction"] = patent_jurisdiction(entry)
        groups["patents" if category == "patents" else "papers"].append(row)
    for rows in groups.values():
        rows.sort(key=lambda r: (r["year"], r["category"], r["month"], r["title"].lower()))
    groups.update(start=start, as_of=as_of, recent_start=max(start, as_of.year - 4),
                  counts=Counter(r["category"] for rows in groups.values() for r in rows))
    return groups


def plot_svg(groups: dict, start: int, as_of: date, compact: bool = False) -> str:
    """Two independent stacks per year, one symbol per record, shared count scale."""
    by_year = {year: {kind: [r for r in groups[kind] if r["year"] == year]
                      for kind in ("papers", "patents")}
               for year in range(start, as_of.year + 1)}
    maximum = max((len(rows) for kinds in by_year.values() for rows in kinds.values()), default=0)
    step = 18 if compact else 14
    width = max(680, 40 + len(by_year) * 128) if compact else max(1000,48+len(by_year)*190)
    height = max(340 if compact else 280, maximum * step + 100)
    column_width = (width - 48) / max(1, len(by_year))
    baseline = height - 75
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" class="activity-plot" viewBox="0 0 {width} {height}" font-family="Arial, sans-serif" role="group" aria-label="Papers and patent records by year from {start} to {as_of.year}">',
             '<desc>Each year has papers on the left and patent records on the right, on the same count scale. Counts are separate, not added. Choose a symbol or stack label to inspect its records.</desc>']
    for column, (year, kinds) in enumerate(by_year.items()):
        center = 24 + (column + .5) * column_width
        if column:
            boundary = 24 + column * column_width
            parts.append(f'<line x1="{boundary}" y1="8" x2="{boundary}" y2="{height-8}" stroke="#e6edeb" pointer-events="none"/>')
        for kind, offset in (("papers", -.19), ("patents", .19)):
            records = kinds[kind]
            x = center + offset * column_width
            color = "#326c79" if kind == "papers" else "#8b6938"
            count_y = baseline - len(records) * step - 12
            parts.append(f'<text x="{x}" y="{count_y}" text-anchor="middle" font-size="13" font-weight="600" fill="{color}" data-stack-kind="{kind}" data-stack-year="{year}" data-stack-count="{len(records)}">{len(records)}</text>')
            for index, row in enumerate(records):
                y = baseline - (index + .5) * step
                jurisdiction = row.get("jurisdiction", "unknown")
                label_kind = LABELS[row["category"]] if kind == "papers" else "Patent record · " + JURISDICTIONS[jurisdiction]
                label = f'{year} · {label_kind} · {row["title"]}'
                jurisdiction_attr = f' data-jurisdiction="{jurisdiction}"' if kind == "patents" else ""
                parts.append(f'<a href="#history-{kind}-{year}" class="history-dot" data-history-kind="{kind}" data-history-year="{year}" data-history-key="{row["id"]}"{jurisdiction_attr} aria-label="{esc(label)}"><title>{esc(label)}</title><rect x="{x-12}" y="{y-7}" width="24" height="14" fill="transparent"/>')
                if kind == "papers" and row["category"] == "conferences":
                    parts.append(f'<rect x="{x-3.6}" y="{y-3.6}" width="7.2" height="7.2" transform="rotate(45 {x} {y})" fill="{color}"/>')
                elif kind == "patents" and jurisdiction == "unknown":
                    parts.append(f'<rect x="{x-4}" y="{y-4}" width="8" height="8" fill="#899a9f"/>')
                else:
                    fill = "#fff" if kind == "patents" and jurisdiction == "KR" else color
                    parts.append(f'<circle cx="{x}" cy="{y}" r="4.2" fill="{fill}" stroke="{color}" stroke-width="1.4"/>')
                parts.append("</a>")
            stack_label = "Papers" if kind == "papers" else "Patents"
            parts.append(f'<a href="#history-{kind}-{year}" class="history-year-link" data-history-kind="{kind}" data-history-year="{year}" aria-label="{year}: {len(records)} {kind}"><rect x="{x-32}" y="{baseline+4}" width="64" height="28" fill="transparent"/><text x="{x}" y="{baseline+23}" text-anchor="middle" font-size="12" fill="{color}">{stack_label}</text></a>')
        year_label = str(year) + ("*" if year == as_of.year else "")
        parts.append(f'<text x="{center}" y="{baseline+53}" text-anchor="middle" font-size="15" font-weight="700" fill="#294a54">{year_label}</text>')
    parts.append(f'<line x1="24" y1="{baseline}" x2="{width-24}" y2="{baseline}" stroke="#cfdddc" pointer-events="none"/></svg>')
    return "".join(parts)


def year_details(rows: list[dict], kind: str, start: int, as_of: date, roles: dict, members: list[str]) -> str:
    panels = []
    for year in range(start, as_of.year + 1):
        records = [r for r in rows if r["year"] == year]
        entries = []
        for row in reversed(records):
            title = f'<a href="{esc(row["url"])}" target="_blank" rel="noopener">{esc(row["title"])} ↗</a>' if row["url"] else esc(row["title"])
            if kind == "patents":
                names = ", ".join(display_author(n) for n in split_authors(row["entry"].fields.get("author", "")))
                authors = esc(names)
            else:
                authors = render_authors(row["entry"], roles, members)
            kind_label = LABELS[row["category"]] + (" · " + JURISDICTIONS[row["jurisdiction"]] if kind == "patents" else "")
            entries.append(f'''<li id="history-item-{row['id']}" data-history-item="{row['id']}" tabindex="-1">
                <p class="history-kind">{esc(kind_label)}</p><h4>{title}</h4>
                <p class="history-authors">{authors}</p><p class="history-citation">{esc(citation_text(row['entry']))} · {year}</p></li>''')
        empty = '<p class="history-empty">No records for this year in the current library.</p>'
        panels.append(f'''<details class="history-year" id="history-{kind}-{year}" data-history-panel="{kind}-{year}" data-history-count="{len(records)}">
            <summary>{year} · {'Papers' if kind == 'papers' else 'Patents'} <span>{len(records)} {'papers' if kind == 'papers' else 'patent records'}</span></summary>
            {f'<ol>{"".join(entries)}</ol>' if entries else empty}</details>''')
    return "".join(panels)


def activity_section(activity: dict, recent_papers: list[dict], roles: dict, members: list[str], directions: int, citations: dict | None = None) -> str:
    start, as_of = activity["start"], activity["as_of"]
    paper_count, patent_count = len(activity["papers"]), len(activity["patents"])
    counts = activity["counts"]
    annual_start = max(start, ANNUAL_START_YEAR)
    earlier = {kind: [r for r in activity[kind] if r["year"] < annual_start]
               for kind in ("papers", "patents")}
    annual = {kind: [r for r in activity[kind] if r["year"] >= annual_start]
              for kind in ("papers", "patents")}
    earlier_papers = Counter(r["category"] for r in earlier["papers"])
    earlier_summary = f'''<aside class="earlier-research" aria-labelledby="earlier-research-heading">
        <div><p class="eyebrow">{start}–{annual_start-1} · CUMULATIVE</p><h3 id="earlier-research-heading">Earlier research</h3>
        <p>Academic and industrial research</p></div>
        <div class="earlier-stat" data-earlier-kind="papers"><strong>{len(earlier['papers'])}</strong><span>Papers</span><small>{earlier_papers['journals']} journal · {earlier_papers['conferences']} conference</small></div>
        <div class="earlier-stat" data-earlier-kind="patents"><strong>{len(earlier['patents'])}</strong><span>Patent records</span><small>Applications &amp; grants</small></div>
      </aside>'''
    details = ''.join(f'<div class="history-detail-group" data-trend-panel="{kind}"><h4 class="history-detail-heading">{kind.title()}</h4><div class="history-years">{year_details(annual[kind],kind,annual_start,as_of,roles,members)}</div></div>' for kind in ("papers", "patents"))
    unknown_legend = '<span><i class="patent-unknown-marker"></i>Unspecified office</span>' if any(r.get("jurisdiction")=="unknown" for r in annual["patents"]) else ''
    trend = f'''<section class="history-trend" id="trend-combined" aria-labelledby="trend-combined-heading">
        <div class="trend-heading"><div><p class="eyebrow">RESEARCH OUTPUT</p><h3 id="trend-combined-heading">Papers &amp; patents by year</h3><p>Select a dot to explore.</p></div>
        <div class="history-legend"><div><b>Papers</b><span><i class="journal-marker"></i>Journal</span><span><i class="conference-marker"></i>Conference</span></div><div><b>Patents</b><span><i class="patent-kr-marker"></i>Korea (KR)</span><span><i class="patent-marker"></i>Outside Korea</span>{unknown_legend}</div></div></div>
        <div class="history-scroll" tabindex="0" role="region" aria-label="Scrollable papers and patents timeline">{plot_svg(annual,annual_start,as_of,compact=bool(citations))}</div>
        <p class="history-axis-note"><span>KR coverage: partial</span><span>* Through {as_of.strftime('%d %b %Y')}</span></p>
        <div class="history-selection-tools" hidden><p class="history-selection-status" role="status" aria-live="polite"></p><button type="button" class="history-close">Close selection ×</button></div>
        {details}
      </section>'''
    return f'''<section class="research-activity" id="research-activity" aria-labelledby="activity-heading">
      <div class="activity-intro"><div><p class="eyebrow">RESEARCH AT A GLANCE</p><h2 id="activity-heading">Ideas, built over time.</h2></div>
        <p>Research by Changwook Jeong and collaborators, across academic and industrial settings.</p></div>
      <div class="activity-stats">
        <div class="activity-stat"><strong>{paper_count}</strong><h3>Papers since {start}</h3><p>{counts['journals']} journal · {counts['conferences']} conference</p></div>
        <div class="activity-stat"><strong>{patent_count}</strong><h3>Patent records since {start}</h3><p>Applications &amp; grants</p></div>
        <div class="activity-stat"><strong>{len(recent_papers)}</strong><h3>Papers in the past 12 months</h3><p><a href="#research-heading">Explore the latest research ↓</a></p></div>
        <div class="activity-stat"><strong>{directions}</strong><h3>Connected research areas</h3><p>Materials · devices · memory · AI</p></div>
      </div>
      {earlier_summary}
      <div class="history-heading"><div><p class="eyebrow">{annual_start} → {as_of.year} · ANNUAL OUTPUT</p><h2>Research at UNIST</h2></div>
        <p class="annual-totals">{len(annual['papers'])} papers <span>·</span> {len(annual['patents'])} patent records</p></div>
      {'<div class="trend-comparison">' + trend + citation_section(citations,annual_start,as_of.year) + '</div>' if citations else trend}
      <details class="activity-method disclosure-note"><summary>About these figures</summary>
      <p>Counts come from our publication library and update with the bibliography. Papers exclude invited talks, books and patents. The {start}–{annual_start-1} period is summarized cumulatively, not plotted as an annual data point; annual charts start in {annual_start}. By record year since joining UNIST in {annual_start}; some records may reflect work begun earlier. Industrial research output is not fully reflected in public records.</p>
      <p>Domestic (KR) coverage is incomplete and will be expanded. Patent records include applications and grants, not unique inventions or patent families. Patent years follow each library record, which may represent an application, publication or grant; national counterparts and related records may be counted separately. These are not patent-family counts or a measure of current legal status. No first-online date, filing date or priority date is inferred.</p></details>
      <a class="activity-library-link" href="../" target="_blank" rel="noopener">Publication &amp; patent library ↗</a>
    </section>'''
