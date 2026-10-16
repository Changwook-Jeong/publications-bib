import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_activity as activity
import build_explorer as explorer
from build_publications import parse_bibtex

AS_OF=date(2026,10,17)


class ActivityTests(unittest.TestCase):
    def test_current_library_counts_reconcile(self):
        data=activity.load_activity(ROOT/"publications.bib",ROOT/"research-summaries.json",AS_OF)
        entries=parse_bibtex((ROOT/"publications.bib").read_text(encoding="utf-8-sig"))
        expected=[e for e in entries if activity.entry_category(e) in activity.LABELS and 2007<=activity.entry_year(e)<=AS_OF.year and not (activity.entry_year(e)==AS_OF.year and activity.entry_month(e)>AS_OF.month)]
        self.assertEqual(sum(len(data[k]) for k in ("papers","patents")),len(expected))
        self.assertEqual(data["counts"],Counter(activity.entry_category(e) for e in expected))
        self.assertEqual(data["recent_start"],2022)
        self.assertTrue(all(r["year"]>=2007 for k in ("papers","patents") for r in data[k]))

    def test_cutoffs_and_record_not_family_counting(self):
        bib="""
        @article{old,year={2006},title={Old}}
        @article{first,year={2007},title={First}}
        @inproceedings{conf,year={2026},month={jun},title={Conference}}
        @inproceedings{talk,year={2026},title={[Invited Talk] Not a paper}}
        @book{book,year={2026},title={Book}}
        @patent{krA,year={2024},number={KR20240000001A},title={Same invention}}
        @patent{krB,year={2026},number={KR102900000B1},title={Same invention}}
        @patent{us,year={2026},publisher={US Patent 12,000,000},title={US record}}
        @patent{futureMonth,year={2026},month={nov},title={Future}}
        @article{futureYear,year={2027},title={Future}}
        """
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            (p/"lib.bib").write_text(bib)
            (p/"data.json").write_text(json.dumps({"papers":[]}))
            data=activity.load_activity(p/"lib.bib",p/"data.json",AS_OF)
        self.assertEqual(len(data["papers"]),2)
        self.assertEqual(len(data["patents"]),3)
        self.assertEqual(Counter(r["jurisdiction"] for r in data["patents"]),{"KR":2,"non-KR":1})

    def test_jurisdiction_follows_number_not_assignee(self):
        cases=[
            ("number={KR102817884B1}","KR"),
            ("number={US12400119B2},country={Korea}","non-KR"),
            ("publisher={U.S. Patent 1234567}","non-KR"),
            ("publisher={US Patent App. 13/919,049}","non-KR"),
            ("number={WO2020000123A1}","non-KR"),
            ("assignee={UNIST Korea}","unknown"),
        ]
        for fields,expected in cases:
            entry=parse_bibtex("@patent{k,title={T},"+fields+"}")[0]
            self.assertEqual(activity.patent_jurisdiction(entry),expected)

    def test_svg_each_symbol_matches_one_record_and_every_year_exists(self):
        data=activity.load_activity(ROOT/"publications.bib",ROOT/"research-summaries.json",AS_OF)
        for kind in ("papers","patents"):
            svg=activity.plot_svg(data[kind],kind,2007,AS_OF,2022)
            tree=ET.fromstring(svg)
            symbols=[e for e in tree.iter() if "data-history-key" in e.attrib]
            self.assertEqual(len(symbols),len(data[kind]))
            self.assertEqual(len({e.attrib["data-history-key"] for e in symbols}),len(symbols))
            labels=[e for e in tree.iter() if e.attrib.get("class")=="history-year-link"]
            self.assertEqual(len(labels),20)
            self.assertIn("2026*",svg)
            self.assertIn('fill="#edf4f0"',svg)
            self.assertIn('fill-opacity="0.43"',svg)

    def test_patent_open_and_solid_symbols_and_unknown(self):
        rows=[dict(id="a",year=2026,title="Domestic",jurisdiction="KR"),
              dict(id="b",year=2026,title="Foreign",jurisdiction="non-KR"),
              dict(id="c",year=2026,title="Unknown",jurisdiction="unknown")]
        tree=ET.fromstring(activity.plot_svg(rows,"patents",2007,AS_OF,2022))
        symbols={e.attrib["data-history-key"]:e for e in tree.iter() if "data-history-key" in e.attrib}
        self.assertEqual(list(symbols["a"])[-1].attrib["fill"],"#fff")
        self.assertEqual(list(symbols["b"])[-1].attrib["fill"],"#8b6938")
        self.assertEqual(list(symbols["c"])[-1].attrib["fill"],"#899a9f")

    def test_unsafe_urls_and_editorial_escaping(self):
        for url in ("file:///C:/private","javascript:alert(1)","https://127.0.0.1/private"):
            entry=parse_bibtex("@patent{k,title={T},url={"+url+"}}")[0]
            self.assertEqual(activity.public_link(entry,{}),"")
        svg=activity.plot_svg([dict(id="safe",year=2026,category="journals",title='<script>alert("x")</script>')],"papers",2007,AS_OF,2022)
        self.assertNotIn("<script>",svg)
        self.assertIn("&lt;script&gt;",svg)

    def test_build_has_both_trends_and_excludes_private_export(self):
        with tempfile.TemporaryDirectory() as temp:
            explorer.build(Path(temp),as_of=AS_OF)
            page=(Path(temp)/"index.html").read_text(encoding="utf-8")
            self.assertIn('id="trend-papers"',page)
            self.assertIn('id="trend-patents"',page)
            self.assertIn("not unique inventions",page)
            self.assertIn("Domestic (KR) coverage is incomplete",page)
            self.assertIn('id="history-papers-2015"',page)
            self.assertIn("No records for this year",page)
            self.assertTrue((Path(temp)/"research-activity.js").exists())
            for private in ("export (1).xlsx","의뢰번호","관리번호","현재상태명","zotero_files","C:\\Users"):
                self.assertNotIn(private,page)


if __name__=="__main__":
    unittest.main()
