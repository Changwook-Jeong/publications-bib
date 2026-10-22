#!/usr/bin/env python3
"""Rolling paper gallery. New library records get honest abstract-only cards."""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import re
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import build_research as summaries
from build_activity import activity_section, load_activity
from build_citations import load_snapshot
from build_publications import (
    citation_text, clean_tex, entry_category, entry_month, entry_year,
    display_author, load_members, load_roles, parse_bibtex, render_authors, split_authors,
)

ROOT, GROUP, esc = summaries.ROOT, summaries.GROUP, summaries.esc
TOPICS = {
    "devices": "Device physics",
    "materials": "Materials & processing",
    "memory": "Memory & computing",
    "ai": "AI & design",
    "other": "More research",
}


def window_start(as_of: date) -> date:
    day = min(as_of.day, calendar.monthrange(as_of.year - 1, as_of.month)[1])
    return as_of.replace(year=as_of.year - 1, day=day)


def date_interval(entry, dates: dict) -> tuple[date, date]:
    year, month = entry_year(entry), entry_month(entry)
    if exact := dates.get(entry.key):
        parsed = date.fromisoformat(exact)
        # A future bibliography correction takes precedence over a stale day.
        if parsed.year == year and (not month or parsed.month == month):
            return parsed, parsed
    if month:
        return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    return date(year, 1, 1), date(year, 12, 31)


def safe_url(value: str) -> str:
    if not value:
        return ""
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Invalid public paper URL")
    if parsed.hostname in {"localhost", "::1"} or re.fullmatch(r"[\d.]+", parsed.hostname):
        raise ValueError("Local/IP URLs cannot be published")
    return value


def load_catalog(data_path: Path, bib_path: Path, as_of: date) -> list[dict]:
    curated = {p["citation_key"]: p for p in summaries.load_summaries(data_path, bib_path)}
    dates = json.loads(data_path.read_text(encoding="utf-8")).get("publication_dates", {})
    papers = []
    for entry in parse_bibtex(bib_path.read_text(encoding="utf-8-sig")):
        if entry_category(entry) not in {"journals", "conferences"} or not entry_year(entry):
            continue
        start, end = date_interval(entry, dates)
        if end < window_start(as_of) or start > as_of:
            continue
        if entry.key in curated:
            paper = dict(curated[entry.key])
            paper["areas"] = paper.get("areas") or [
                "devices" if paper["topic"] == "Device physics" else
                "ai" if paper["topic"] == "Physics-grounded AI" else "materials"]
        else:
            title = clean_tex(entry.fields.get("title", ""))
            doi = clean_tex(entry.fields.get("doi", ""))
            url = "https://doi.org/" + doi if doi else clean_tex(entry.fields.get("url", ""))
            paper = dict(citation_key=entry.key, entry=entry,
                         slug="paper-" + hashlib.sha256(entry.key.encode()).hexdigest()[:12],
                         title=title, headline=title,
                         summary=clean_tex(entry.fields.get("abstract", "")), takeaway="",
                         year=entry_year(entry), month=entry_month(entry), doi=doi, url=safe_url(url),
                         venue=clean_tex(entry.fields.get("journal") or entry.fields.get("booktitle", "")),
                         full_text_checked=False, areas=["other"], topic=TOPICS["other"])
            paper["date_label"] = f'{summaries.MONTH_NAMES[paper["month"]]} {paper["year"]}'.strip()
        if not paper["areas"] or any(area not in TOPICS for area in paper["areas"]):
            raise ValueError("Invalid research area")
        paper["sort_date"] = start.isoformat()
        paper["date_precision"] = "day" if start == end else "month" if paper["month"] else "year"
        if paper["date_precision"] == "year":
            paper["date_label"] += " · month not recorded"
        papers.append(paper)
    return sorted(papers, key=lambda p: (p["sort_date"], p["title"].lower()), reverse=True)


def short_venue(paper: dict) -> str:
    for pattern, short in (("Electron Device Letters", "IEEE EDL"), ("Design Automation", "DAC"),
                           ("Learning Representations", "ICLR"), ("Machine Learning", "ICML"),
                           ("Reliability Physics", "IEEE IRPS")):
        if pattern.lower() in paper["venue"].lower():
            return short
    return paper["venue"]


def card(paper: dict, index: int) -> str:
    excerpt = paper.get("card_summary") or paper["takeaway"] or paper["summary"][:190] + ("…" if len(paper["summary"]) > 190 else "")
    search = " ".join([paper["title"], paper["headline"], paper["summary"], paper["venue"],
                       " ".join(TOPICS[area] for area in paper["areas"]),
                       clean_tex(paper["entry"].fields.get("author", ""))])
    return f'''<article class="research-card area-{esc(paper['areas'][0])}" data-topic="{esc(' '.join(paper['areas']))}" data-search="{esc(search)}" data-date="{esc(paper['sort_date'])}" data-slug="{esc(paper['slug'])}">
      <div class="card-top"><span class="topic"><i aria-hidden="true"></i>{esc(TOPICS[paper['areas'][0]])}</span><span class="card-index">{index:02d}</span></div>
      <p class="card-date">{esc(short_venue(paper))} <span aria-hidden="true">/</span> {esc(paper['date_label'])}</p>
      <h3><a class="summary-link" href="{esc(paper['slug'])}/" data-paper="{esc(paper['slug'])}" aria-haspopup="dialog">{esc(paper['headline'])}</a></h3>
      <p class="card-summary">{esc(excerpt)}</p>
      <div class="card-bottom"><span class="paper-kind">{'Journal article' if entry_category(paper['entry']) == 'journals' else 'Conference paper'}</span>
      <a class="read-link summary-link" href="{esc(paper['slug'])}/" data-paper="{esc(paper['slug'])}" aria-label="Explore: {esc(paper['headline'])}" aria-haspopup="dialog">{'Read insight' if paper['full_text_checked'] else 'View paper'} <span aria-hidden="true">↗</span></a></div>
    </article>'''


def detail_page(paper: dict, papers: list[dict], roles: dict, members: list[str]) -> str:
    if paper["full_text_checked"]:
        return paper_metadata(summaries.detail_page(paper, papers[:3], roles, members),paper)
    original = f'<a class="paper-link" href="{esc(paper["url"])}" target="_blank" rel="noopener">Read original paper ↗</a>' if paper["url"] else "<p>Primary-source link not yet recorded.</p>"
    page = summaries.shell(paper["headline"], f'''<main id="main" class="detail-main">
      <a class="back-link" href="../">← Research explorer</a><header class="article-header">
      <p class="eyebrow">{esc(paper['date_label'])} / {esc(short_venue(paper))}</p><h1>{esc(paper['title'])}</h1>
      <p class="article-dek">Added automatically from our publication library.</p></header>
      <div class="article-body"><section class="scope-box"><h2>From the paper's abstract</h2>
      <p>{esc(paper['summary']) if paper['summary'] else 'No abstract is recorded in the library yet.'}</p></section>
      <p class="source-disclosure">A full-text explanation has not yet been prepared. This card does not claim a full-text review.</p>
      <section class="paper-reference"><h2>Original paper</h2><p class="authors">{render_authors(paper['entry'], roles, members)}</p>
      <p class="citation">{esc(citation_text(paper['entry']))} · {paper['year']}</p>{original}</section></div></main>''',
      asset_prefix="../", detail=True)
    return paper_metadata(page,paper)


def paper_metadata(page: str, paper: dict) -> str:
    """Bibliographic facts only; never mark an unreviewed explanation indexable."""
    authors = [display_author(n) for n in split_authors(paper['entry'].fields.get('author',''))]
    tags = {'citation_title':paper['title'], 'citation_publication_date':str(paper['year']),
            'citation_doi':paper.get('doi',''), 'citation_journal_title':paper['venue']}
    # Do not misidentify a conference venue as a journal.
    if entry_category(paper['entry']) == 'conferences':
        tags['citation_conference_title'] = tags.pop('citation_journal_title')
    metadata = ''.join(f'<meta name="{k}" content="{esc(v)}">' for k,v in tags.items() if v)
    metadata += ''.join(f'<meta name="citation_author" content="{esc(a)}">' for a in authors)
    canonical = summaries.PUBLIC_RESEARCH + paper['slug'] + '/'
    metadata += f'<link rel="canonical" href="{esc(canonical)}">'
    scholarly = {'@context':'https://schema.org','@type':'ScholarlyArticle','headline':paper['title'],
                 'author':[{'@type':'Person','name':a} for a in authors],
                 'isPartOf':{'@type':'CreativeWork','name':paper['venue']},
                 'datePublished':str(paper['year']), 'url':paper['url']}
    if paper.get('doi'):
        scholarly['identifier'] = {'@type':'PropertyValue','propertyID':'DOI','value':paper['doi']}
    metadata += '<script type="application/ld+json">' + json.dumps(scholarly,ensure_ascii=False).replace('<','\\u003c') + '</script>'
    return page.replace('</head>',metadata+'</head>').replace(
        'content="Recent semiconductor research explained by the Jeong Research Group at UNIST."',
        f'content="{esc(paper["title"] + ". " + paper["venue"] + ", " + str(paper["year"]) + ". Bibliographic details and an AI-assisted explanation; consult the original paper.")}"')


def group_context(papers: list[dict]) -> str:
    chosen = ['cryogenic-transistors','chip-scale-multiphysics','semimetal-contact-physics']
    by_slug = {p['slug']:p for p in papers}
    items = []
    for slug in chosen:
        if paper := by_slug.get(slug):
            items.append(f'<li><a href="{esc(slug)}/">{esc(paper["title"])}</a><span>{esc(short_venue(paper))} · {paper["year"]}</span><a class="evidence-source" href="{esc(paper["url"])}" target="_blank" rel="noopener">Original paper ↗</a></li>')
    return f'''<section class="group-context" aria-labelledby="group-context-heading">
      <div><p class="eyebrow">JEONG RESEARCH GROUP · UNIST</p><h2 id="group-context-heading">Semiconductor physics, computation &amp; intelligent design.</h2>
      <p>Led by Prof. <a href="{GROUP}team" target="_top">Changwook Jeong (정창욱)</a> at Ulsan National Institute of Science and Technology (UNIST), Ulsan, Republic of Korea.</p>
      <p>We connect semiconductor materials and interfaces, carrier transport, device reliability, emerging memory and computing devices, and physics-grounded AI.</p>
      <nav aria-label="Research group information"><a href="{GROUP}research" target="_top">Research areas ↗</a><a href="{GROUP}team" target="_top">PI &amp; team ↗</a><a href="{GROUP}join-us" target="_top">Joining the group ↗</a></nav></div>
      <details class="selected-evidence"><summary>Selected papers · direct sources</summary><ul>{''.join(items)}</ul><p>Bibliographic facts and primary-source links. Explanatory summaries remain AI-assisted and not author-reviewed.</p></details>
    </section>'''


def group_schema() -> dict:
    return {'@context':'https://schema.org','@graph':[
        {'@type':'Organization','@id':GROUP+'#group','name':'Jeong Research Group',
         'url':GROUP,'parentOrganization':{'@type':'CollegeOrUniversity','name':'Ulsan National Institute of Science and Technology (UNIST)'},
         'description':'Semiconductor materials and interfaces, carrier transport, reliability, memory and computing devices, and physics-grounded AI.'},
        {'@type':'Person','@id':GROUP+'team#changwook-jeong','name':'Changwook Jeong',
         'alternateName':'정창욱','url':GROUP+'team','affiliation':{'@type':'CollegeOrUniversity','name':'UNIST'},
         'sameAs':['https://scholar.google.com/citations?user=CPYw1roAAAAJ&hl=en']}]}


def overview(papers: list[dict], as_of: date, roles: dict, members: list[str], activity: dict | None = None, citations: dict | None = None) -> str:
    cards = "\n".join(card(p, i) for i, p in enumerate(papers, 1))
    topics = [(k,v) for k,v in TOPICS.items() if any(k in p["areas"] for p in papers)]
    filters = f'<button type="button" class="filter-button active" data-filter="all" aria-pressed="true">All research <span>{len(papers)}</span></button>'
    filters += "".join(f'<button type="button" class="filter-button" data-filter="{k}" aria-pressed="false">{esc(v)} <span>{sum(k in p["areas"] for p in papers)}</span></button>' for k,v in topics)
    templates = []
    for paper in papers:
        body = detail_page(paper, papers, roles, members).split('<main id="main" class="detail-main">', 1)[1].split("</main>", 1)[0]
        body = re.sub(r'<a class="back-link".*?</a>', "", body, count=1)
        body = body.split('<aside class="related">',1)[0]
        body = body.replace("<h1>", '<h2 id="reader-title">',1).replace("</h1>", "</h2>",1)
        body += f'<a class="full-page-link" href="{esc(paper["slug"])}/" target="_blank" rel="noopener">Open as a separate page ↗</a>'
        templates.append(f'<template id="summary-{esc(paper["slug"])}">{body}</template>')
    content = f'''<main id="main">
      <section class="hero"><div><p class="eyebrow">A WINDOW INTO OUR RESEARCH</p><h1>Ideas in motion.<br><em>Physics at the core.</em></h1></div>
        <div class="hero-description"><p>Explore the questions, discoveries and design possibilities behind our latest papers.</p><p class="hero-note">From atomic-scale materials to devices, memory and intelligent design.</p></div></section>
      {group_context(papers)}
      {activity_section(activity, papers, roles, members, len(TOPICS)-1, citations) if activity else ''}
      <section class="research-section" aria-labelledby="research-heading">
        <div class="section-heading"><div><p class="eyebrow">RECENT 12 MONTHS</p><h2 id="research-heading">Research explorer <span class="collection-count">{len(papers)}</span></h2></div>
          <a class="text-link" href="{GROUP}publications" target="_top">All publications ↗</a></div>
        <div class="explorer-tools" hidden><div class="topic-filters" role="group" aria-label="Filter by research topic">{filters}</div>
          <div class="utility-row"><label class="search-field"><span aria-hidden="true">⌕</span><input type="search" id="research-search" placeholder="Search a topic, paper or author" aria-label="Search research"></label>
          <label class="sort-field"><span>Sort</span><select id="research-sort" aria-label="Sort papers"><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></label>
          <div class="view-options" role="group" aria-label="Choose layout"><button type="button" data-view="grid" aria-pressed="true">Grid</button><button type="button" data-view="list" aria-pressed="false">List</button></div></div></div>
        <div class="collection-meta"><p id="result-count" role="status" aria-live="polite">{len(papers)} papers · newest first</p><p>{window_start(as_of).strftime('%d %b %Y')} – {as_of.strftime('%d %b %Y')}</p></div>
        <div class="research-grid" id="research-grid">{cards}</div>
        <div class="empty-state" hidden><h3>No papers match this view.</h3><p>Try another topic or a broader search.</p><button type="button" id="reset-filters">Reset filters</button></div>
        <p class="editorial-note">AI-assisted summaries · not author-reviewed</p>
        <details class="summary-method disclosure-note"><summary>About the summaries</summary><p>Dates follow our library; journal issue dates may differ from first-online dates. Month-only records include the boundary month, and year-only records are labeled. Topics are browsing aids, not mutually exclusive categories. AI-assisted explanations are based on the full texts and are not author-reviewed; automatically added abstract-only records are identified separately.</p></details>
      </section>
      <section class="join-strip"><div><p class="eyebrow">YOUR NEXT RESEARCH QUESTION</p><h2>Find a question that moves you.</h2><p>Connect materials, processes, device behavior and data-driven design.</p></div>
        <a class="join-link" href="{GROUP}join-us" target="_top">Explore opportunities at UNIST ↗</a></section>
      <dialog class="research-reader" id="research-reader" aria-labelledby="reader-title">
        <div class="reader-toolbar"><span>RESEARCH EXPLORER</span><div><button type="button" id="reader-prev" aria-label="Previous paper">←</button><span id="reader-position"></span><button type="button" id="reader-next" aria-label="Next paper">→</button><button type="button" id="reader-close">Close <span aria-hidden="true">×</span></button></div></div>
        <div class="reader-scroll"><div id="reader-content"></div></div></dialog>
      {''.join(templates)}
    </main>'''
    css_version = hashlib.sha256((ROOT / "web" / "research.css").read_bytes()).hexdigest()[:12]
    return summaries.shell("Research explorer", content,
        description="Jeong Research Group at UNIST, led by Prof. Changwook Jeong (정창욱): semiconductor materials, transport, reliability, memory devices and physics-grounded AI.",
        canonical=summaries.PUBLIC_RESEARCH, structured_data=group_schema()).replace(
        'href="research.css"', f'href="research.css?v={css_version}"').replace(
        '<script src="research.js"></script>',
        '<script src="research-activity.js"></script>\n  <script src="research.js"></script>')


def build(output: Path, data: Path = ROOT / "research-summaries.json", bib: Path = ROOT / "publications.bib", as_of: date | None = None, index_overview: bool = False) -> list[dict]:
    # GitHub runners use UTC; the group's publication window follows Korea time.
    as_of = as_of or datetime.now(timezone(timedelta(hours=9))).date()
    papers = load_catalog(data, bib, as_of)
    curated = summaries.load_summaries(data, bib)
    roles, members = load_roles(ROOT / "author-roles.json"), load_members(ROOT / "group-members.json")
    activity = load_activity(bib, data, as_of)
    output.mkdir(parents=True, exist_ok=True)
    snapshot_path = ROOT / 'citation-metrics.json'
    citations = load_snapshot(snapshot_path) if snapshot_path.exists() else None
    page = overview(papers, as_of, roles, members, activity, citations)
    if index_overview:
        page = page.replace('content="noindex, nofollow"','content="index, follow"')
    (output / "index.html").write_text(page, encoding="utf-8")
    # Keep old deep links alive when their papers leave the recent-paper window.
    for paper in {p["slug"]:p for p in [*curated,*papers]}.values():
        folder = output / paper["slug"]
        folder.mkdir(exist_ok=True)
        (folder / "index.html").write_text(detail_page(paper, papers, roles, members), encoding="utf-8")
    for name in ("research.css", "research.js", "research-activity.js"):
        shutil.copyfile(ROOT / "web" / name, output / name)
    return papers


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "_site" / "research-preview")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None)
    parser.add_argument("--index-overview", action="store_true", help="Release opt-in after review; detail explanations remain noindex.")
    args = parser.parse_args()
    papers = build(args.output, as_of=args.as_of, index_overview=args.index_overview)
    print(f"Built explorer: {len(papers)} recent papers; {sum(p['full_text_checked'] for p in papers)} full-text explanations")
