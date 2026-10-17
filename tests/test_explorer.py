import hashlib
import json
import re
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_explorer as explorer
from build_publications import parse_bibtex

AS_OF = date(2026, 10, 17)


class ExplorerTests(unittest.TestCase):
    def test_recent_window_uses_library_dates_and_excludes_talks_patents(self):
        papers = explorer.load_catalog(ROOT / "research-summaries.json", ROOT / "publications.bib", AS_OF)
        self.assertGreaterEqual(len(papers), 15)
        keys = {p["citation_key"] for p in papers}
        self.assertNotIn("huhContextInformedNeuralODEs2025a", keys)
        self.assertIn("kimMobilityOverestimationThinFilm2025a", keys)
        self.assertNotIn("jeongDimensionlessPhysicsRobust2026", keys)
        self.assertIn("cryogenic-transistors", {p["slug"] for p in papers})
        self.assertEqual([p["sort_date"] for p in papers], sorted((p["sort_date"] for p in papers), reverse=True))
        unknown = next(p for p in papers if p["slug"] == "tracking-ions-in-memory")
        self.assertIn("month not recorded", unknown["date_label"])

    def test_leap_day_and_date_precision(self):
        self.assertEqual(explorer.window_start(date(2024,2,29)), date(2023,2,28))
        entry = parse_bibtex("@article{k,year={2026},month={jun},title={T}}")[0]
        self.assertEqual(explorer.date_interval(entry, {}), (date(2026,6,1),date(2026,6,30)))
        self.assertEqual(explorer.date_interval(entry, {"k":"2026-05-02"}), (date(2026,6,1),date(2026,6,30)))

    def test_new_paper_gets_honest_abstract_card_without_ai_invention(self):
        with tempfile.TemporaryDirectory() as temp:
            bib = Path(temp) / "library.bib"
            bib.write_text((ROOT/"publications.bib").read_text(encoding="utf-8-sig") +
                           "\n@article{newPaper,year={2026},month={sep},title={New <test> paper},journal={Test Journal},abstract={Library abstract.},doi={10.1234/test}}", encoding="utf-8")
            papers = explorer.load_catalog(ROOT/"research-summaries.json", bib, AS_OF)
            paper = next(p for p in papers if p["citation_key"] == "newPaper")
            self.assertFalse(paper["full_text_checked"])
            self.assertEqual(paper["areas"], ["other"])
            page = explorer.detail_page(paper, papers, {}, [])
            self.assertIn("A full-text explanation has not yet been prepared", page)
            self.assertIn("Library abstract.", page)
            self.assertIn("New &lt;test&gt; paper", page)
            self.assertNotIn("What we found", page)

    def test_dialog_templates_and_filter_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            papers = explorer.build(Path(temp), as_of=AS_OF)
            overview = (Path(temp)/"index.html").read_text()
            self.assertEqual(overview.count('<article class="research-card'),len(papers))
            self.assertEqual(overview.count('<template id="summary-'),len(papers))
            self.assertIn('aria-labelledby="reader-title"',overview)
            self.assertIn('aria-live="polite"',overview)
            self.assertIn('data-view="list"',overview)
            self.assertIn('id="research-search"',overview)
            self.assertIn("17 Oct 2025",overview)
            css_version=hashlib.sha256((ROOT/"web"/"research.css").read_bytes()).hexdigest()[:12]
            self.assertIn(f'href="research.css?v={css_version}"',overview)
            for area,label in explorer.TOPICS.items():
                if any(area in p["areas"] for p in papers):
                    self.assertIn(f'data-filter="{area}"',overview)
            for private in ("zotero_files","C:\\Users","sourcePath","118.131.244.26"):
                self.assertNotIn(private,overview)

    def test_older_summary_urls_survive(self):
        with tempfile.TemporaryDirectory() as temp:
            entries = parse_bibtex((ROOT/"publications.bib").read_text(encoding="utf-8-sig"))
            latest_year = max(explorer.entry_year(e) for e in entries)
            papers = explorer.build(Path(temp), as_of=date(latest_year+2,1,1))
            self.assertEqual(papers,[])
            self.assertTrue((Path(temp)/"cryogenic-transistors"/"index.html").exists())

    def test_safe_primary_links(self):
        for url in ("javascript:alert(1)", "file:///C:/private", "https://127.0.0.1/x", "https://user:password@example.com"):
            with self.assertRaises(ValueError):
                explorer.safe_url(url)
        self.assertEqual(explorer.safe_url("https://openreview.net/forum?id=abc"),"https://openreview.net/forum?id=abc")

    def test_topic_border_palette_and_primary_area_mapping(self):
        css=(ROOT/"web"/"research.css").read_text(encoding="utf-8")
        borders=[]
        for area in explorer.TOPICS:
            rule=re.search(r'\.research-card\.area-'+area+r'\{([^}]+)\}',css)
            self.assertIsNotNone(rule,area)
            border=re.search(r'--card-border:(#[0-9a-f]{6})',rule.group(1))
            self.assertIsNotNone(border,area)
            borders.append(border.group(1))
        self.assertEqual(len(set(borders)),len(explorer.TOPICS))
        self.assertIn('border:2px solid var(--card-border)',css)
        self.assertIn('border-top:5px solid var(--card-accent)',css)
        self.assertIn('border-left:5px solid var(--card-accent)',css)
        self.assertIn('background:linear-gradient(180deg,var(--card-tint),#fff 110px)',css)
        self.assertIn('background:var(--card-tint);border:1px solid var(--card-border)',css)
        paper=dict(explorer.load_catalog(ROOT/"research-summaries.json",ROOT/"publications.bib",AS_OF)[0])
        paper["areas"]=["ai","devices"]
        card=explorer.card(paper,1)
        self.assertIn('class="research-card area-ai"',card)
        self.assertIn('data-topic="ai devices"',card)
        self.assertIn('AI &amp; design',card)


if __name__ == "__main__":
    unittest.main()
