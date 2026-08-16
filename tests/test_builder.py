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

    def test_group_members_are_underlined_by_class(self):
        source = """@article{demo2026,
          title = {Demo},
          author = {Kim, Taehyun and Jeong, Changwook},
          year = 2026
        }"""
        entry = MODULE.parse_bibtex(source)[0]
        rendered = MODULE.render_authors(entry, {}, ["Taehyun Kim"])
        self.assertIn('class="author member">Taehyun Kim', rendered)
        self.assertIn('class="author pi">Changwook Jeong', rendered)

    def test_pi_corresponding_rules_and_exceptions(self):
        root = Path(__file__).parents[1]
        entries = MODULE.parse_bibtex((root / "publications.bib").read_text(encoding="utf-8-sig"))
        by_key = {entry.key: entry for entry in entries}
        roles = MODULE.load_roles(root / "author-roles.json")
        automatic_2026 = MODULE.role_names(by_key["huhScalingTheoryNonlinear2026"], roles, "corresponding")
        excluded_2026 = MODULE.role_names(by_key["islamThicknessScalingRoughnessInduced2026"], roles, "corresponding")
        last_author = MODULE.role_names(by_key["jangUnifiedMechanismStrain2026"], roles, "corresponding")
        self.assertIn("Changwook Jeong", automatic_2026)
        self.assertNotIn("Changwook Jeong", excluded_2026)
        self.assertIn("Changwook Jeong", last_author)

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

    def test_configured_role_names_match_bibliography_authors(self):
        root = Path(__file__).parents[1]
        entries = MODULE.parse_bibtex((root / "publications.bib").read_text(encoding="utf-8-sig"))
        by_key = {entry.key: entry for entry in entries}
        roles = MODULE.load_roles(root / "author-roles.json")
        configured_keys = [key for key in roles if not key.startswith("_")]
        self.assertGreaterEqual(len(configured_keys), 19)
        for key in configured_keys:
            self.assertIn(key, by_key)
            authors = MODULE.split_authors(by_key[key].fields.get("author", ""))
            for role in ("corresponding", "equal"):
                for name in roles[key].get(role, []):
                    self.assertTrue(
                        any(MODULE.name_has_role(author, [name]) for author in authors),
                        f"{key}: {name} is not in the BibTeX author list",
                    )

    def test_embed_mode_is_available_without_replacing_standalone_header(self):
        root = Path(__file__).parents[1]
        template = (root / "web" / "index.template.html").read_text(encoding="utf-8")
        styles = (root / "web" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("get('embed') === '1'", template)
        self.assertIn(".embed .site-header", styles)
        self.assertIn('<header class="site-header">', template)

    def test_team_roster_loads(self):
        root = Path(__file__).parents[1]
        members = MODULE.load_members(root / "group-members.json")
        self.assertIn("Taehyun Kim", members)
        self.assertIn("Hyeonwoo Lee", members)
        self.assertGreaterEqual(len(members), 30)


if __name__ == "__main__":
    unittest.main()
