import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_research as research


class ResearchTests(unittest.TestCase):
    def test_selected_papers_are_full_text_grounded_and_sorted(self):
        papers = research.load_summaries(ROOT / "research-summaries.json", ROOT / "publications.bib")
        self.assertEqual(len(papers), 3)
        self.assertEqual([paper["month"] for paper in papers], [8, 7, 6])
        self.assertTrue(all(paper["full_text_checked"] for paper in papers))
        self.assertEqual(papers[1]["doi"], "10.1145/3770743.3803918")

    def test_unverified_summary_is_rejected(self):
        data = json.loads((ROOT / "research-summaries.json").read_text(encoding="utf-8"))
        data["papers"][0]["full_text_checked"] = False
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "data.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inspected full text"):
                research.load_summaries(path, ROOT / "publications.bib")

    def test_build_is_separate_and_does_not_publish_local_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "research-preview"
            papers = research.build(output)
            overview = (output / "index.html").read_text(encoding="utf-8")
            self.assertEqual(len(list(output.rglob("*.html"))), 4)
            self.assertIn('class="research-grid"', overview)
            self.assertIn('get(\'embed\')===\'1\'', overview)
            self.assertIn('content="noindex, nofollow"', overview)
            self.assertIn("not author-reviewed", overview)
            for paper in papers:
                page = (output / paper["slug"] / "index.html").read_text(encoding="utf-8")
                for section in ("question", "approach", "findings", "significance", "scope", "paper"):
                    self.assertIn(f'id="{section}"', page)
                self.assertIn(f'https://doi.org/{paper["doi"]}', page)
                self.assertIn("not reviewed by the authors", page)
                for private in ("zotero_files", "C:\\Users", "sourcePath", "118.131.244.26"):
                    self.assertNotIn(private, page)
            self.assertFalse(list(output.rglob("*.pdf")))
            self.assertTrue((output / "research.css").exists())
            self.assertTrue((output / "research.js").exists())

    def test_metadata_is_read_from_bibliography(self):
        papers = research.load_summaries(ROOT / "research-summaries.json", ROOT / "publications.bib")
        self.assertEqual(papers[0]["venue"], "IEEE Electron Device Letters")
        self.assertIn("1671", research.citation_text(papers[0]["entry"]))

    def test_editorial_content_is_escaped(self):
        papers = research.load_summaries(ROOT / "research-summaries.json", ROOT / "publications.bib")
        paper = dict(papers[0], headline='<script>alert("x")</script>')
        rendered = research.card(paper, 1)
        self.assertNotIn('<script>alert', rendered)
        self.assertIn('&lt;script&gt;', rendered)

    def test_duplicate_and_unsafe_slugs_are_rejected(self):
        for slug in ("../private", "cryogenic-transistors"):
            data = json.loads((ROOT / "research-summaries.json").read_text(encoding="utf-8"))
            data["papers"][1]["slug"] = slug
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "data.json"
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValueError):
                    research.load_summaries(path, ROOT / "publications.bib")


if __name__ == "__main__":
    unittest.main()
