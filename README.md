# Jeong Research Group publications

This repository keeps the Better BibTeX export used by the group website and builds a responsive publication page for GitHub Pages.

## Local preview

```powershell
python scripts/build_publications.py --output _site
python -m http.server 8765 --directory _site
```

## Author-role markers

The page displays `*` for corresponding authors and `†` for equal-contribution authors. Roles can be supplied in either of two ways.

### Zotero Extra fields (recommended)

Add lines like these to the item's **Extra** field:

```text
tex.corresponding: Changwook Jeong
tex.equal: First Author; Second Author
```

Better BibTeX exports them as custom `corresponding` and `equal` fields, which the builder reads automatically.

### Repository mapping

Alternatively, add a record to `author-roles.json` using its BibTeX citation key:

```json
{
  "citationKey": {
    "corresponding": ["Changwook Jeong"],
    "equal": ["First Author", "Second Author"]
  }
}
```

Names are matched after punctuation, spaces, and BibTeX formatting have been normalized. No role is inferred from author order except for the PI rules explicitly recorded in `_rules`.

The initial repository mapping was transcribed from the role legends and explicit author markers in the PI's CV and accomplishments statement. A configured role is tested against the current BibTeX author list during every build.

The group roster in `group-members.json` is matched to publication authors and rendered with an underline. Corresponding-author rules supplied by the PI are kept in `_rules` within `author-roles.json`; explicit per-paper records still take precedence and can add co-corresponding or equal-contribution authors.

## Google Sites embed

Use the following URL for the Google Sites **Embed → By URL** block:

```text
https://changwook-jeong.github.io/publications-bib/?embed=1
```

The `embed=1` view hides the standalone GitHub Pages header and footer, leaving the white filters and publication records for integration into the Google Sites page. The normal URL keeps the complete branded standalone layout.

## Deployment

The Pages workflow rebuilds the site whenever the bibliography, role metadata, generator, or design changes. The existing BibBase cache-refresh workflow remains in place during the preview period.

## Full-text-based research preview

The separate preview is at `https://changwook-jeong.github.io/publications-bib/research-preview/`.
Append `?embed=1` to hide the standalone masthead, hero and footer. This is a public GitHub
Pages preview with `noindex`, not a private page. It is not linked from or embedded
in the live Google Sites homepage yet, and the current publications page is unchanged.

```powershell
python scripts/build_publications.py --output _site
python scripts/build_explorer.py --output _site/research-preview
python -m http.server 8765 --directory _site
```

`research-summaries.json` contains original explanatory copy keyed to the Zotero /
Better BibTeX citation key. Titles, authors, roles, journal / conference metadata and
ordering are obtained from `publications.bib` at build time. The DAC DOI override
was read from the stored full paper; it does not modify the source Zotero item.

Each summary has a question, approach, findings, significance, scope / limitations,
and a primary-source link. `full_text_checked` means the full text was inspected;
it does **not** mean an author approved the explanation. The preview discloses its
AI-assisted, not-author-reviewed status. No PDFs, source-page images, local paths,
extracted text files, or private research material belong in this repository.

The research explorer shows journal and conference papers in a rolling 12-month
window at build time, using Korea time. Patents and invited talks remain in Publications, not this
gallery. Each normal bibliography update rebuilds both pages. There is no additional
scheduled task: a quiet library's time window advances on its next build.

The gallery offers overlapping topic filters, title/author/venue/topic search,
newest/oldest sorting, Grid/List layouts and an accessible native-dialog reader.
The dialog supports previous/next in the current filtered set, Escape to close,
focus return, and preservation of the gallery's scroll position. URL query
parameters preserve browsing filters; a paper fragment can open its explanation
directly. Motion is brief and user-triggered, with reduced-motion preferences
respected. No carousel or automatic floating animation is used.

Cards use a subtle full-border color and a stronger top edge for their displayed
primary research area: devices blue, materials green, memory ochre, AI muted
purple, and unclassified records gray. Overlapping topic filters are unchanged;
color is a secondary cue alongside the visible topic label. List view retains
the same palette with a stronger left edge.

`publication_dates` complements the bibliography's year/month with previously
verified library days. These are library publication/issue dates, not necessarily
online-first dates. A changed bibliography year/month supersedes the stored day.
Month-only records include the overlapping boundary month; year-only records are
labeled and sort at the start of their year without inventing a month.

New papers added to Zotero automatically get bibliographic/abstract-only cards
if they fall in the window, even before a narrative explanation exists. These are
explicitly identified as not full-text reviewed and are not assigned invented
findings or research areas. Preparing a full-text explanation still requires
reading its source and adding a summary record. The 15 initial explanations are
AI-assisted and not author-reviewed. Old summary URLs remain available after
their cards leave the recent window. No PDFs or private paths are published.

For a reproducible date-window check:

```powershell
python scripts/build_explorer.py --as-of 2026-10-17 --output _site/research-preview
python -m unittest discover -s tests
node --test tests/activity.test.cjs
```

## Research activity since 2007

The research preview adds a bibliography-derived statistics strip and a paired
Papers / Patents timeline. This does not change the Google Sites pages.

- Papers include journal and conference records from 2007 through the build date;
  invited talks, books and patents are excluded from paper counts.
- Patent counts are library records, not unique inventions or families. Related
  national records and application/grant records may appear separately.
- The year is the existing bibliography's year; priority and filing dates are not
  inferred. Future years/months and verified future days are excluded.
- The 2007–2021 period is a separate cumulative summary of earlier academic and
  industrial research, never a column on an annual chart. Annual timelines start
  in 2022, with period-specific paper and patent totals above the chart. These are
  record years, not assertions about where or when the underlying work was done.
- Each year has two separate stacks: papers on the left, patent records on the
  right, on the same count scale. They are never added into a combined total.
  Journal circles and conference diamonds are teal; patent symbols are ochre.
  There is no recent-five-year background or opacity emphasis. Empty annual
  years stay visible. A stack label/symbol reveals its bibliographic records.
- Patent symbols are open circles for KR and solid circles for other identified
  jurisdictions. Unspecified jurisdictions use squares, never guessed from an
  inventor or assignee's location. Domestic coverage remains incomplete until the
  user imports the confirmed records into Zotero.
- No university export, unpublished application, internal ID or management status
  is copied into this repository. The supplied domestic export has not been imported.

The current user requested no computer-use actions. Validation for this update
uses Python data/SVG/HTML tests and Node interaction-controller tests without
controlling a browser or Zotero. Browser layout QA is deferred.
