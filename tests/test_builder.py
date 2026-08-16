import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "build_publications.py"
SPEC = importlib.util.spec_from_file_location("build_publications", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class BuilderTests(unittest.TestCase):
    def test_nested_braces_and_fields_parse(self):
        source = """@article{demo2026,
          title = {A {{Nested}} Title},
          author = {Huh, In and Jeong, Changwook},
          year = 2026,
          journal = {IEEE Test Journal}
        }"""
        entries = MODULE.parse_bibtex(source)
        self.assertEqual(len(entries), 1)
        self.assertEqual(MODULE.clean_tex(entries[0].fields["title"]), "A Nested Title")
        self.assertEqual(MODULE.entry_category(entries[0]), "journals")

    def test_latex_math_and_accents_are_readable(self):
        self.assertEqual(MODULE.clean_title(r"Buckingham {$\pi$}-Invariant"), "Buckingham π-Invariant")
        self.assertEqual(MODULE.clean_title(r"Poincar\'e and 750 {$^\circ$}C"), "Poincaré and 750 °C")

    def test_role_markers_render_without_changing_names(self):
        source = """@article{demo2026,
          title = {Demo},
          author = {Huh, In and Islam, Mir and Jeong, Changwook},
          year = 2026
        }"""
        entry = MODULE.parse_bibtex(source)[0]
        roles = {"demo2026": {"corresponding": ["Changwook Jeong"], "equal": ["In Huh", "Mir Islam"]}}
        rendered = MODULE.render_authors(entry, roles)
        self.assertIn("Changwook Jeong<sup", rendered)
        self.assertIn("In Huh<sup", rendered)
        self.assertIn("Mir Islam<sup", rendered)

    def test_full_library_build(self):
        root = Path(__file__).parents[1]
        entries = MODULE.parse_bibtex((root / "publications.bib").read_text(encoding="utf-8-sig"))
        with tempfile.TemporaryDirectory() as temp_dir:
            page = MODULE.build_page(entries, {}, (root / "web" / "index.template.html").read_text(encoding="utf-8"))
            output = Path(temp_dir) / "index.html"
            output.write_text(page, encoding="utf-8")
            self.assertGreater(len(entries), 100)
            self.assertIn("A Scaling Theory", page)
            self.assertIn('data-category="patents"', page)


if __name__ == "__main__":
    unittest.main()
