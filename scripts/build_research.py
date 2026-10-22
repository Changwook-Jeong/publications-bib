#!/usr/bin/env python3
"""Build a separate, full-text-grounded research-summary preview.

No PDFs, local attachment paths, or extracted full texts are published. Bibliographic
metadata is read from the existing export; explanatory copy lives in a small JSON file.
This does not generate summaries for newly added papers without a separate authoring step.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path

from build_publications import (
    citation_text, clean_tex, entry_category, entry_month, entry_year,
    load_members, load_roles, parse_bibtex, render_authors,
)

ROOT = Path(__file__).resolve().parents[1]
GROUP = "https://sites.google.com/view/jeong-research-group/"
PUBLIC_RESEARCH = "https://changwook-jeong.github.io/publications-bib/research-preview/"
MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_summaries(data_path: Path, bib_path: Path) -> list[dict]:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported summary schema")
    by_key = {entry.key: entry for entry in parse_bibtex(bib_path.read_text(encoding="utf-8-sig"))}
    seen_keys, seen_slugs, papers = set(), set(), []
    required = ("citation_key", "slug", "topic", "headline", "summary", "takeaway",
                "question", "approach", "findings", "significance", "scope", "skills",
                "source_note", "source_locator")
    for original in data.get("papers", []):
        paper = dict(original)
        if not all(paper.get(field) for field in required):
            raise ValueError("Missing summary content")
        if paper.get("full_text_checked") is not True:
            raise ValueError("Preview summaries require an inspected full text")
        if paper["citation_key"] in seen_keys or paper["slug"] in seen_slugs:
            raise ValueError("Duplicate summary key or slug")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", paper["slug"]):
            raise ValueError("Unsafe summary slug")
        entry = by_key.get(paper["citation_key"])
        if not entry or entry_category(entry) not in {"journals", "conferences"}:
            raise ValueError("Summary must match a journal or conference paper")
        if not isinstance(paper["findings"], list) or len(paper["findings"]) < 2:
            raise ValueError("At least two findings are required")
        doi = paper.get("doi") or clean_tex(entry.fields.get("doi", ""))
        if doi and not re.fullmatch(r"10\.\d{4,9}/[^\s<>\"']+", doi):
            raise ValueError("A valid primary-paper DOI is required")
        url = "https://doi.org/" + doi if doi else paper.get("url", "")
        if not re.fullmatch(r"https://(?:openreview\.net|proceedings\.mlr\.press|doi\.org)/[^\s<>\"']+", url):
            raise ValueError("A valid primary-paper DOI or publisher URL is required")
        paper.update(entry=entry, doi=doi, url=url, year=entry_year(entry), month=entry_month(entry),
                     title=clean_tex(entry.fields.get("title", "")),
                     venue=clean_tex(entry.fields.get("journal") or entry.fields.get("booktitle", "")))
        paper["date_label"] = f'{MONTH_NAMES[paper["month"]]} {paper["year"]}'.strip()
        seen_keys.add(paper["citation_key"])
        seen_slugs.add(paper["slug"])
        papers.append(paper)
    return sorted(papers, key=lambda paper: (-paper["year"], -paper["month"], paper["title"].lower()))


def shell(title: str, content: str, *, asset_prefix: str = "", detail: bool = False,
          description: str = "Recent semiconductor research explained by the Jeong Research Group at UNIST.",
          canonical: str = "", structured_data: dict | None = None) -> str:
    canonical_meta = f'<link rel="canonical" href="{esc(canonical)}">' if canonical else ''
    json_ld = ('<script type="application/ld+json">' + json.dumps(structured_data,ensure_ascii=False).replace('<','\\u003c') + '</script>') if structured_data else ''
    return f'''<!doctype html>
<html lang="en"><head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow"><meta name="color-scheme" content="light">
  <meta name="description" content="{esc(description)}">
  {canonical_meta}{json_ld}
  <title>{esc(title)} · Jeong Research Group</title>
  <script>if(new URLSearchParams(location.search).get('embed')==='1')document.documentElement.classList.add('embed');</script>
  <link rel="stylesheet" href="{asset_prefix}research.css">
</head><body class="{'detail-page' if detail else 'overview-page'}">
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="masthead"><div class="masthead-inner">
    <a class="brand" href="{GROUP}" target="_top"><span class="brand-symbol" aria-hidden="true">Ψ</span>Jeong Research Group</a>
    <div class="masthead-meta"><span>UNIST</span><span class="preview-label">Research preview</span></div>
  </div></header>
  {content}
  <footer class="site-footer"><div><strong>Jeong Research Group</strong><p>Semiconductor physics, computation and intelligence.</p></div>
    <a href="{GROUP}" target="_top">Group website <span aria-hidden="true">↗</span></a></footer>
  <script src="{asset_prefix}research.js"></script>
</body></html>'''


def card(paper: dict, index: int) -> str:
    return f'''<article class="research-card" data-topic="{esc(paper['topic'])}">
  <div class="card-top"><span class="topic">{esc(paper['topic'])}</span><span class="card-index">0{index}</span></div>
  <p class="card-date">{esc(paper['venue'])} <span aria-hidden="true">·</span> {esc(paper['date_label'])}</p>
  <h3><a class="summary-link" href="{esc(paper['slug'])}/">{esc(paper['headline'])}</a></h3>
  <p class="card-summary">{esc(paper['summary'])}</p>
  <div class="card-bottom"><p class="takeaway"><span>THE INSIGHT</span>{esc(paper['takeaway'])}</p>
  <a class="read-link summary-link" href="{esc(paper['slug'])}/" aria-label="Read summary: {esc(paper['headline'])}">Read the research <span aria-hidden="true">↗</span></a></div>
</article>'''


def overview(papers: list[dict]) -> str:
    cards = "\n".join(card(paper, index) for index, paper in enumerate(papers, 1))
    content = f'''<main id="main">
  <section class="hero"><p class="eyebrow">RESEARCH IN FOCUS</p><h1>Recent work.<br><em>Clearly explained.</em></h1>
    <div class="hero-description"><p>From atomic-scale defects to chip-scale design, explore the questions behind our latest research.</p>
    <p class="hero-note">Three recent studies. Original papers linked throughout.</p></div></section>
  <section class="research-section" aria-labelledby="research-heading"><div class="section-heading">
    <div><p class="eyebrow">PHYSICS → UNDERSTANDING → DESIGN</p><h2 id="research-heading">Latest research</h2></div>
    <a class="text-link" href="{GROUP}publications" target="_top">All publications <span aria-hidden="true">↗</span></a></div>
    <div class="research-grid">{cards}</div>
    <p class="editorial-note">Selected recent papers, shown newest first. AI-assisted explanations based on the full texts; not author-reviewed. Consult the original papers for methods, evidence and scope.</p>
  </section>
  <section class="join-strip"><div><p class="eyebrow">YOUR NEXT RESEARCH QUESTION</p><h2>Explore the physics.<br>Help design what comes next.</h2>
    <p>Our work connects materials, processing, device behavior and data-driven design.</p></div>
    <a class="join-link" href="{GROUP}join-us" target="_top">Explore opportunities at UNIST <span aria-hidden="true">↗</span></a></section>
</main>'''
    return shell("Research in focus", content)


def detail_page(paper: dict, papers: list[dict], roles: dict, members: list[str]) -> str:
    findings = "".join(f"<li>{esc(finding)}</li>" for finding in paper["findings"])
    skills = "".join(f'<span>{esc(skill)}</span>' for skill in paper["skills"])
    other = "".join(f'<a href="../{esc(item["slug"])}/"><span>{esc(item["topic"])}</span>{esc(item["headline"])} <b aria-hidden="true">↗</b></a>' for item in papers if item["slug"] != paper["slug"])
    citation = citation_text(paper["entry"])
    content = f'''<main id="main" class="detail-main">
  <a class="back-link" href="../">← All research summaries</a>
  <header class="article-header"><p class="eyebrow">{esc(paper['topic'])} <span aria-hidden="true">/</span> {esc(paper['date_label'])}</p>
    <h1>{esc(paper['headline'])}</h1><p class="article-dek">{esc(paper['summary'])}</p>
    <div class="insight-callout"><span>THE INSIGHT</span><p>{esc(paper['takeaway'])}</p></div></header>
  <div class="article-layout"><nav class="article-nav" aria-label="Summary sections">
    <a href="#question">The question</a><a href="#approach">Our approach</a><a href="#findings">What we found</a><a href="#significance">Why it matters</a><a href="#scope">Scope &amp; limits</a><a href="#paper">Original paper</a></nav>
    <div class="article-body">
      <section id="question"><h2>The question</h2><p>{esc(paper['question'])}</p></section>
      <section id="approach"><h2>Our approach</h2><p>{esc(paper['approach'])}</p></section>
      <section id="findings"><h2>What we found</h2><ol class="findings">{findings}</ol></section>
      <section id="significance"><h2>Why it matters</h2><p>{esc(paper['significance'])}</p><div class="skills" aria-label="Research connections">{skills}</div></section>
      <section id="scope" class="scope-box"><h2>Scope &amp; limits</h2><p>{esc(paper['scope'])}</p></section>
      <section id="paper" class="paper-reference"><p class="eyebrow">ORIGINAL PAPER</p><h2>{esc(paper['title'])}</h2>
        <p class="authors">{render_authors(paper['entry'], roles, members)}</p><p class="citation">{esc(citation)} · {paper['year']}</p>
        <p class="author-legend">* Corresponding author · † Equal contribution · Underlined: group member</p>
        <a class="paper-link" href="{esc(paper['url'])}" target="_blank" rel="noopener">Read the original paper <span aria-hidden="true">↗</span></a>
        <details><summary>About this explanation</summary><p>AI-assisted summary checked against the full text, not reviewed by the authors. {esc(paper['source_note'])}</p><p>Evidence locations: {esc(paper['source_locator'])}. This page does not reproduce or redistribute the source PDF.</p></details></section>
    </div></div><aside class="related"><h2>Continue exploring</h2><div>{other}</div></aside>
</main>'''
    return shell(paper["headline"], content, asset_prefix="../", detail=True)


def build(output: Path, data: Path = ROOT / "research-summaries.json", bib: Path = ROOT / "publications.bib") -> list[dict]:
    papers = load_summaries(data, bib)
    if not papers:
        raise ValueError("No summaries to build")
    roles, members = load_roles(ROOT / "author-roles.json"), load_members(ROOT / "group-members.json")
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(overview(papers), encoding="utf-8")
    for paper in papers:
        folder = output / paper["slug"]
        folder.mkdir(exist_ok=True)
        (folder / "index.html").write_text(detail_page(paper, papers, roles, members), encoding="utf-8")
    for name in ("research.css", "research.js"):
        shutil.copyfile(ROOT / "web" / name, output / name)
    return papers


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "_site" / "research-preview")
    args = parser.parse_args()
    papers = build(args.output)
    print(f"Built {len(papers)} full-text-based research summaries into {args.output}")
