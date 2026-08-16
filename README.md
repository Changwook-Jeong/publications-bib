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

Names are matched after punctuation, spaces, and BibTeX formatting have been normalized. No marker is inferred from author order; role data must be explicit.

## Deployment

The Pages workflow rebuilds the site whenever the bibliography, role metadata, generator, or design changes. The existing BibBase cache-refresh workflow remains in place during the preview period.
