#!/usr/bin/env python3
"""Build a responsive publications page from a Better BibTeX export.

The builder intentionally uses only the Python standard library so the same
command works locally and in GitHub Actions without dependency installation.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


@dataclass
class BibEntry:
    entry_type: str
    key: str
    fields: dict[str, str]
    raw: str


def read_group(text: str, start: int, opener: str, closer: str) -> tuple[str, int]:
    depth = 0
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[start + 1 : index], index + 1
    raise ValueError(f"Unclosed BibTeX group starting at character {start}")


def parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    position = 0
    while position < len(body):
        while position < len(body) and (body[position].isspace() or body[position] == ","):
            position += 1
        match = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", body[position:])
        if not match:
            break
        name = match.group(1).lower()
        position += match.end()
        if position >= len(body):
            fields[name] = ""
            break
        if body[position] == "{":
            value, position = read_group(body, position, "{", "}")
        elif body[position] == '"':
            value, position = read_group(body, position, '"', '"')
        else:
            end = position
            while end < len(body) and body[end] != ",":
                end += 1
            value = body[position:end].strip()
            position = end
        fields[name] = value.strip()
    return fields


def parse_bibtex(text: str) -> list[BibEntry]:
    entries: list[BibEntry] = []
    position = 0
    while True:
        marker = text.find("@", position)
        if marker < 0:
            break
        header = re.match(r"@([A-Za-z]+)\s*\{", text[marker:])
        if not header:
            position = marker + 1
            continue
        entry_type = header.group(1).lower()
        group_start = marker + header.end() - 1
        content, entry_end = read_group(text, group_start, "{", "}")
        comma = content.find(",")
        if comma < 0:
            position = entry_end
            continue
        key = content[:comma].strip()
        body = content[comma + 1 :]
        entries.append(
            BibEntry(
                entry_type=entry_type,
                key=key,
                fields=parse_fields(body),
                raw=text[marker:entry_end].strip(),
            )
        )
        position = entry_end
    return entries


def clean_tex(value: str) -> str:
    if not value:
        return ""
    value = re.sub(r"\{\\relax\s+([^{}]+)\}", r"\1", value)
    value = re.sub(r"\{?\$\\pi\$\}?", "π", value)
    value = re.sub(r"\{?\$\\mu\$\}?", "μ", value)
    value = re.sub(r"\{?\$\\gamma\$\}?", "γ", value)
    value = re.sub(r"\{?\$\\cdot\$\}?", "·", value)
    value = re.sub(r"\{?\$\^\\circ\$\}?", "°", value)
    subscript_map = str.maketrans("0123456789+-", "₀₁₂₃₄₅₆₇₈₉₊₋")
    value = re.sub(
        r"\{?\$_\{([^{}]+)\}\$\}?",
        lambda match: match.group(1).translate(subscript_map),
        value,
    )
    accent_map = {"'": "\u0301", "`": "\u0300", "^": "\u0302", '"': "\u0308", "~": "\u0303"}
    value = re.sub(
        r"\\(['`\^\"~])\{?([A-Za-z])\}?",
        lambda match: unicodedata.normalize("NFC", match.group(2) + accent_map[match.group(1)]),
        value,
    )
    replacements = {
        r"\&": "&",
        r"\%": "%",
        r"\_": "_",
        r"\#": "#",
        r"\AA": "Å",
        r"\aa": "å",
        "--": "–",
        "~": " ",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(r"\\[A-Za-z]+\*?(?:\[[^]]*\])?\s*", "", value)
    value = value.replace("{", "").replace("}", "")
    value = re.sub(r"\$([^$]+)\$", r"\1", value)
    return re.sub(r"\s+", " ", value).strip()


def clean_title(value: str) -> str:
    title = clean_tex(value)
    formulas = {
        "In2O3": "In₂O₃",
        "Al2O3": "Al₂O₃",
        "MoS2": "MoS₂",
        "SiO2": "SiO₂",
        "HfO2": "HfO₂",
    }
    for plain, formatted in formulas.items():
        title = re.sub(rf"\b{plain}\b", formatted, title)
    title = re.sub(r"\bCm2\.V-1·s-1\s*", "cm²·V⁻¹·s⁻¹ ", title)
    title = re.sub(r"\bcm2\.V-1·s-1\s*", "cm²·V⁻¹·s⁻¹ ", title)
    title = re.sub(r"([A-Za-z])-\s+([A-Za-z])", r"\1-\2", title)
    return title


def split_authors(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in re.split(r"\s+and\s+", value) if part.strip()]


def author_parts(raw_name: str) -> tuple[str, str]:
    cleaned = clean_tex(raw_name).strip()
    if "," in cleaned:
        family, given = [part.strip() for part in cleaned.split(",", 1)]
        return given, family
    parts = cleaned.split()
    if len(parts) < 2:
        return "", cleaned
    return " ".join(parts[:-1]), parts[-1]


def display_author(raw_name: str) -> str:
    given, family = author_parts(raw_name)
    return f"{given} {family}".strip()


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", clean_tex(value).lower())


def is_pi(raw_name: str) -> bool:
    given, family = author_parts(raw_name)
    if normalized_name(family) != "jeong":
        return False
    normalized_given = normalized_name(given)
    return normalized_given in {"changwook", "cw", "cwj"}


def role_names(entry: BibEntry, roles: dict[str, object], role: str) -> list[str]:
    names: list[str] = []
    configured = roles.get(entry.key, {})
    if isinstance(configured, dict):
        value = configured.get(role, [])
        if isinstance(value, list):
            names.extend(str(item) for item in value)
        elif isinstance(value, str):
            names.extend(re.split(r"\s*;\s*", value))

    field_name = "corresponding" if role == "corresponding" else "equal"
    raw_field = entry.fields.get(field_name, "")
    if raw_field:
        names.extend(re.split(r"\s*;\s*", clean_tex(raw_field)))

    if role == "corresponding" and entry_category(entry) in {"journals", "conferences"}:
        authors = split_authors(entry.fields.get("author", ""))
        pi_names = [display_author(author) for author in authors if is_pi(author)]
        rules = roles.get("_rules", {})
        if isinstance(rules, dict) and pi_names:
            if rules.get("pi_last_author_is_corresponding") and authors and is_pi(authors[-1]):
                names.extend(pi_names)
            year_rules = rules.get("pi_corresponding_by_year", {})
            if isinstance(year_rules, dict):
                year_rule = year_rules.get(str(entry_year(entry)), {})
                if isinstance(year_rule, dict):
                    categories = year_rule.get("categories", [])
                    excluded = year_rule.get("exclude_keys", [])
                    if entry_category(entry) in categories and entry.key not in excluded:
                        names.extend(pi_names)
    return [name for name in names if name]


def name_has_role(raw_name: str, candidates: list[str]) -> bool:
    raw_norm = normalized_name(raw_name)
    display_norm = normalized_name(display_author(raw_name))
    return any(normalized_name(candidate) in {raw_norm, display_norm} for candidate in candidates)


def entry_category(entry: BibEntry) -> str:
    text = " ".join(
        [entry.fields.get("title", ""), entry.fields.get("keywords", ""), entry.fields.get("note", "")]
    ).lower()
    if entry.entry_type == "patent":
        return "patents"
    if "invited talk" in clean_tex(text).lower() or "invited" in clean_tex(text).lower():
        return "invited"
    if entry.entry_type == "article":
        return "journals"
    if entry.entry_type in {"inproceedings", "conference", "proceedings"}:
        return "conferences"
    return "other"


def entry_year(entry: BibEntry) -> int:
    match = re.search(r"\d{4}", entry.fields.get("year", ""))
    return int(match.group(0)) if match else 0


def entry_month(entry: BibEntry) -> int:
    value = clean_tex(entry.fields.get("month", "")).lower().strip(". ")
    if value.isdigit():
        return max(0, min(12, int(value)))
    return MONTHS.get(value[:3], 0)


def citation_text(entry: BibEntry) -> str:
    f = entry.fields
    if entry.entry_type == "article":
        journal = clean_tex(f.get("journal", ""))
        volume = clean_tex(f.get("volume", ""))
        number = clean_tex(f.get("number", ""))
        pages = clean_tex(f.get("pages", ""))
        volume_issue = volume + (f"({number})" if number else "")
        chunks = [journal, volume_issue, pages]
    elif entry.entry_type == "patent":
        chunks = [clean_tex(f.get("publisher", ""))]
    else:
        chunks = [clean_tex(f.get("booktitle", "")), clean_tex(f.get("address", ""))]
    return " · ".join(chunk for chunk in chunks if chunk)


def compact_bibtex(entry: BibEntry) -> str:
    keep = ["title", "author", "year", "month", "journal", "booktitle", "volume", "number", "pages", "publisher", "doi", "url"]
    lines = [f"@{entry.entry_type}{{{entry.key},"]
    for field in keep:
        if field in entry.fields and entry.fields[field]:
            lines.append(f"  {field} = {{{entry.fields[field]}}},")
    if len(lines) > 1:
        lines[-1] = lines[-1].rstrip(",")
    lines.append("}")
    return "\n".join(lines)


def load_members(path: Path) -> list[str]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return []
    members: list[str] = []
    for key, value in data.items():
        if not key.startswith("_") and isinstance(value, list):
            members.extend(str(item) for item in value)
    return members


def render_authors(entry: BibEntry, roles: dict[str, object], members: list[str] | None = None) -> str:
    corresponding = role_names(entry, roles, "corresponding")
    equal = role_names(entry, roles, "equal")
    members = members or []
    rendered: list[str] = []
    for raw_name in split_authors(entry.fields.get("author", "")):
        name = html.escape(display_author(raw_name))
        classes = ["author"]
        if is_pi(raw_name):
            classes.append("pi")
        elif name_has_role(raw_name, members):
            classes.append("member")
        marks = ""
        if name_has_role(raw_name, corresponding):
            marks += '<sup title="Corresponding author">*</sup>'
        if name_has_role(raw_name, equal):
            marks += '<sup title="Equal contribution">†</sup>'
        rendered.append(f'<span class="{" ".join(classes)}">{name}{marks}</span>')
    return ", ".join(rendered)


def render_entry(entry: BibEntry, roles: dict[str, object], members: list[str] | None = None) -> str:
    category = entry_category(entry)
    year = entry_year(entry)
    title = html.escape(clean_title(entry.fields.get("title", "Untitled")))
    citation = html.escape(citation_text(entry))
    doi = clean_tex(entry.fields.get("doi", ""))
    url = clean_tex(entry.fields.get("url", ""))
    links: list[str] = []
    if doi:
        links.append(f'<a href="https://doi.org/{html.escape(doi)}" target="_blank" rel="noopener">DOI</a>')
    if url and (not doi or url != f"https://doi.org/{doi}"):
        links.append(f'<a href="{html.escape(url)}" target="_blank" rel="noopener">Link</a>')
    links.append(f'<button class="copy-key" type="button" data-key="{html.escape(entry.key)}">Copy key</button>')
    bibtex = html.escape(compact_bibtex(entry))
    searchable_authors = " ".join(
        display_author(raw_name) for raw_name in split_authors(entry.fields.get("author", ""))
    )
    search_text = " ".join([title, citation, entry.fields.get("author", ""), searchable_authors]).lower()
    return f"""
      <article class="publication" data-category="{category}" data-year="{year}" data-search="{html.escape(search_text)}">
        <div class="publication-main">
          <h3>{title}</h3>
          <p class="authors">{render_authors(entry, roles, members)}</p>
          <p class="venue">{citation}</p>
          <div class="publication-links">{' '.join(links)}</div>
          <details><summary>BibTeX</summary><pre>{bibtex}</pre></details>
        </div>
        <div class="publication-year" aria-label="Publication year">{year or '—'}</div>
      </article>"""


def load_roles(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def build_page(
    entries: list[BibEntry],
    roles: dict[str, object],
    template: str,
    members: list[str] | None = None,
) -> str:
    visible = [entry for entry in entries if entry.entry_type in {"article", "inproceedings", "conference", "proceedings", "patent"}]
    visible.sort(key=lambda item: (-entry_year(item), -entry_month(item), clean_title(item.fields.get("title", "")).lower()))
    grouped: dict[int, list[BibEntry]] = {}
    for entry in visible:
        grouped.setdefault(entry_year(entry), []).append(entry)
    sections = []
    for year, year_entries in grouped.items():
        cards = "\n".join(render_entry(entry, roles, members) for entry in year_entries)
        sections.append(f'<section class="year-section" data-year-section="{year}"><h2>{year or "Undated"}</h2>{cards}</section>')
    counts = {
        "all": len(visible),
        "journals": sum(entry_category(entry) == "journals" for entry in visible),
        "conferences": sum(entry_category(entry) == "conferences" for entry in visible),
        "invited": sum(entry_category(entry) == "invited" for entry in visible),
        "patents": sum(entry_category(entry) == "patents" for entry in visible),
    }
    return template.replace("{{PUBLICATIONS}}", "\n".join(sections)).replace("{{COUNTS_JSON}}", json.dumps(counts))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bib", type=Path, default=Path("publications.bib"))
    parser.add_argument("--roles", type=Path, default=Path("author-roles.json"))
    parser.add_argument("--members", type=Path, default=Path("group-members.json"))
    parser.add_argument("--template", type=Path, default=Path("web/index.template.html"))
    parser.add_argument("--output", type=Path, default=Path("_site"))
    args = parser.parse_args()

    entries = parse_bibtex(args.bib.read_text(encoding="utf-8-sig"))
    page = build_page(
        entries,
        load_roles(args.roles),
        args.template.read_text(encoding="utf-8"),
        load_members(args.members),
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "index.html").write_text(page, encoding="utf-8")
    for asset in ("styles.css", "app.js"):
        (args.output / asset).write_text((Path("web") / asset).read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Built {len(entries)} BibTeX records into {args.output / 'index.html'}")


if __name__ == "__main__":
    main()
