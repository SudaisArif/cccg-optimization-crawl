import unittest
from crawl import IndexParser, canonical, classify, group_papers


class CrawlTests(unittest.TestCase):
    def test_legacy_index_and_deduplication(self):
        p = IndexParser("https://cccg.ca/proceedings/2006/")
        p.feed('<DL><DT>1<DD>A. Author.<BR>A title.<BR>In proceedings.'
               '<BR><A HREF="http://www.cccg.ca/proceedings/2006/a.pdf">PDF</A>'
               '<A HREF="a.pdf">again</A></DL>')
        self.assertEqual(len(p.papers), 1)
        record = next(iter(p.papers.values()))
        self.assertEqual(record["title"], "A title.")
        self.assertEqual(record["authors"], "A. Author.")

    def test_external_links_not_followed(self):
        with self.assertRaises(ValueError):
            canonical("https://example.com/a.pdf")

    def test_reference_only_mentions_are_not_candidates(self):
        self.assertEqual(classify("A geometric theorem.\nReferences\nLinear programming."), [])

    def test_hyphenated_and_multiline_solver_names(self):
        self.assertIn("second-order-cone", classify("We use second-order\ncone programming."))
        self.assertIn("convex-optimization", classify("Use convex optimi-\nzation."))

    def test_geometric_interior_points_are_not_solver_mentions(self):
        self.assertEqual(classify("Choose an interior point of the triangle."), [])
        self.assertIn("interior-point", classify("Use an interior-point method."))
        self.assertNotIn("linear-programming", classify("We use nonlinear programming."))

    def test_short_and_full_versions_are_grouped(self):
        base = dict(year=2007, title="A paper", authors="A. Author", source_type="paper", error=None)
        groups = group_papers([dict(base, url="short.pdf", optimization_terms=[]),
                               dict(base, url="full.pdf", optimization_terms=["linear-programming"])])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["status"], "candidate_unreviewed")
        self.assertEqual(groups[0]["urls"], ["short.pdf", "full.pdf"])


if __name__ == "__main__":
    unittest.main()
