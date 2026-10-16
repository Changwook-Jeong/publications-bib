import json
import re
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
        svg=activity.plot_svg(data,2007,AS_OF)
        tree=ET.fromstring(svg)
        for kind in ("papers","patents"):
            symbols=[e for e in tree.iter() if "data-history-key" in e.attrib and e.attrib["data-history-kind"]==kind]
            self.assertEqual(len(symbols),len(data[kind]))
            self.assertEqual(len({e.attrib["data-history-key"] for e in symbols}),len(symbols))
            labels=[e for e in tree.iter() if e.attrib.get("class")=="history-year-link" and e.attrib["data-history-kind"]==kind]
            self.assertEqual(len(labels),20)
            self.assertIn("2026*",svg)
            self.assertNotIn('fill="#edf4f0"',svg)
            self.assertNotIn('fill-opacity=',svg)

    def test_patent_open_and_solid_symbols_and_unknown(self):
        rows=[dict(id="a",year=2026,title="Domestic",jurisdiction="KR"),
              dict(id="b",year=2026,title="Foreign",jurisdiction="non-KR"),
              dict(id="c",year=2026,title="Unknown",jurisdiction="unknown")]
        tree=ET.fromstring(activity.plot_svg({"papers":[],"patents":rows},2022,AS_OF))
        symbols={e.attrib["data-history-key"]:e for e in tree.iter() if "data-history-key" in e.attrib}
        self.assertEqual(list(symbols["a"])[-1].attrib["fill"],"#fff")
        self.assertEqual(list(symbols["b"])[-1].attrib["fill"],"#8b6938")
        self.assertEqual(list(symbols["c"])[-1].attrib["fill"],"#899a9f")

    def test_unsafe_urls_and_editorial_escaping(self):
        for url in ("file:///C:/private","javascript:alert(1)","https://127.0.0.1/private"):
            entry=parse_bibtex("@patent{k,title={T},url={"+url+"}}")[0]
            self.assertEqual(activity.public_link(entry,{}),"")
        svg=activity.plot_svg({"papers":[dict(id="safe",year=2026,category="journals",title='<script>alert("x")</script>')],"patents":[]},2022,AS_OF)
        self.assertNotIn("<script>",svg)
        self.assertIn("&lt;script&gt;",svg)

    def test_build_has_both_trends_and_excludes_private_export(self):
        with tempfile.TemporaryDirectory() as temp:
            explorer.build(Path(temp),as_of=AS_OF)
            page=(Path(temp)/"index.html").read_text(encoding="utf-8")
            self.assertIn('id="trend-combined"',page)
            self.assertNotIn('class="trend-switch"',page)
            self.assertNotIn("Recent 5 years",page)
            self.assertIn("not unique inventions",page)
            self.assertIn("Domestic (KR) coverage is incomplete",page)
            self.assertNotIn('id="history-papers-2015"',page)
            self.assertIn('id="history-papers-2022"',page)
            self.assertIn("Earlier research",page)
            self.assertIn("2007–2021 · CUMULATIVE",page)
            self.assertIn("Research at UNIST",page)
            self.assertTrue((Path(temp)/"research-activity.js").exists())
            for private in ("export (1).xlsx","의뢰번호","관리번호","현재상태명","zotero_files","C:\\Users"):
                self.assertNotIn(private,page)

    def test_period_summaries_and_annual_symbols_reconcile(self):
        data=activity.load_activity(ROOT/"publications.bib",ROOT/"research-summaries.json",AS_OF)
        page=activity.activity_section(data,[],{},[],4)
        chart=re.search(r'aria-label="Scrollable papers and patents timeline">(<svg.*?</svg>)',page).group(1)
        tree=ET.fromstring(chart)
        self.assertEqual(page.count('class="activity-plot"'),1)
        for kind in ("papers","patents"):
            early=[r for r in data[kind] if r["year"]<=2021]
            annual=[r for r in data[kind] if r["year"]>=2022]
            self.assertIn(f'data-earlier-kind="{kind}"><strong>{len(early)}</strong>',page)
            dots=[e for e in tree.iter() if "data-history-key" in e.attrib and e.attrib["data-history-kind"]==kind]
            self.assertEqual(len(dots),len(annual))
            self.assertEqual(len(early)+len(dots),len(data[kind]))
            self.assertEqual({e.attrib["data-history-year"] for e in tree.iter()
                              if e.attrib.get("class")=="history-year-link"},
                             {str(y) for y in range(2022,2027)})
            self.assertNotIn('data-history-year="2021"',page)
            self.assertNotIn('data-history-year="2007"',page)

    def test_empty_annual_year_keeps_zero_and_details(self):
        svg=activity.plot_svg({"papers":[],"patents":[]},2022,AS_OF)
        self.assertIn('data-history-year="2025"',svg)
        details=activity.year_details([],"papers",2022,AS_OF,{},[])
        self.assertIn('id="history-papers-2025"',details)
        self.assertIn('data-history-count="0"',details)
        self.assertIn("No records for this year",details)

    def test_pair_positions_counts_and_shared_scale(self):
        groups={"papers":[dict(id="j",year=2026,category="journals",title="J"),dict(id="c",year=2026,category="conferences",title="C")],
                "patents":[dict(id="p",year=2026,jurisdiction="non-KR",title="P")]}
        tree=ET.fromstring(activity.plot_svg(groups,2022,AS_OF))
        symbols={e.attrib["data-history-key"]:list(e)[-1] for e in tree.iter() if "data-history-key" in e.attrib}
        self.assertLess(float(symbols["j"].attrib["cx"]),float(symbols["p"].attrib["cx"]))
        self.assertEqual(symbols["j"].attrib["cy"],symbols["p"].attrib["cy"])
        self.assertEqual(symbols["j"].attrib["fill"],symbols["c"].attrib["fill"])
        self.assertNotEqual(symbols["j"].attrib["fill"],symbols["p"].attrib["fill"])
        counts={e.attrib["data-stack-kind"]:int(e.attrib["data-stack-count"]) for e in tree.iter() if e.attrib.get("data-stack-year")=="2026"}
        self.assertEqual(counts,{"papers":2,"patents":1})


if __name__=="__main__":
    unittest.main()
