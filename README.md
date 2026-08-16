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
