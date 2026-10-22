import json
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build_citations as citations
import build_explorer as explorer


class CitationAndSearchTests(unittest.TestCase):
    def test_only_supplied_years_and_estimates_are_plotted(self):
        data = citations.load_snapshot(ROOT/'citation-metrics.json')
        tree = ET.fromstring(citations.citation_plot(data,2022,2027))
        rows = {int(el.attrib['data-citation-year']):int(el.attrib['data-citation-estimate'])
                for el in tree.iter() if 'data-citation-year' in el.attrib}
        self.assertEqual(rows,{2022:240,2023:280,2024:310,2025:390,2026:430})
        self.assertNotIn(2027,rows)
        text = citations.citation_section(data,2022,2026)
        for disclosure in ('Approximate','not citations to UNIST-group papers alone','Not live-synced','Capture date was not recorded','2026 is partial-year'):
            self.assertIn(disclosure,text)

    def test_combined_layout_and_existing_interactions_survive(self):
        with tempfile.TemporaryDirectory() as temp:
            explorer.build(Path(temp),as_of=date(2026,10,22))
            page=(Path(temp)/'index.html').read_text(encoding='utf-8')
        self.assertIn('class="trend-comparison"',page)
        self.assertEqual(page.count('id="trend-combined"'),1)
        self.assertEqual(page.count('id="citation-heading"'),1)
        self.assertIn('data-history-year="2022"',page)
        self.assertIn('id="research-reader"',page)
        self.assertIn('Changwook Jeong (정창욱)',page)
        self.assertIn('Selected papers · direct sources',page)
        self.assertIn('content="noindex, nofollow"',page)

    def test_long_notes_are_collapsed_not_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            explorer.build(Path(temp),as_of=date(2026,10,22))
            page=(Path(temp)/'index.html').read_text(encoding='utf-8')
        for class_name, phrase in (
            ('citation-source', '2026 is partial-year'),
            ('activity-method disclosure-note', 'Domestic (KR) coverage is incomplete'),
            ('summary-method disclosure-note', 'journal issue dates may differ'),
        ):
            panel = re.search(r'<details class="' + re.escape(class_name) + r'"[^>]*>(.*?)</details>',page,re.S)
            self.assertIsNotNone(panel)
            self.assertIn(phrase,panel.group(1))
            self.assertNotIn(' open',panel.group(0).split('>',1)[0])
        self.assertIn('PI citation impact',page)
        self.assertIn('Approximate values · * Partial year',page)
        self.assertIn('KR coverage: partial',page)
        self.assertIn('AI-assisted summaries · not author-reviewed',page)

    def test_release_opt_in_does_not_index_unreviewed_details(self):
        with tempfile.TemporaryDirectory() as temp:
            explorer.build(Path(temp),as_of=date(2026,10,22),index_overview=True)
            overview=(Path(temp)/'index.html').read_text(encoding='utf-8')
            detail=(Path(temp)/'chip-scale-multiphysics'/'index.html').read_text(encoding='utf-8')
        self.assertIn('content="index, follow"',overview)
        self.assertIn('content="noindex, nofollow"',detail)
        self.assertIn('name="citation_title"',detail)
        self.assertIn('name="citation_conference_title"',detail)
        self.assertNotIn('name="citation_journal_title"',detail)
        self.assertIn('name="citation_author"',detail)
        for page in (overview,detail):
            for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>',page,re.S):
                json.loads(block)
            self.assertIn('rel="canonical"',page)


if __name__ == '__main__':
    unittest.main()
