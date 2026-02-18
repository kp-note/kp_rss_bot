import unittest

from src.content import is_probably_paid_substack


class PaidSubstackTests(unittest.TestCase):
    def test_paid_marker_in_html(self):
        html = "<html><body>This post is for paid subscribers</body></html>"
        self.assertTrue(
            is_probably_paid_substack(
                entry_title="Weekly memo",
                entry_url="https://abc.substack.com/p/test",
                html=html,
            )
        )

    def test_non_paid_simple_post(self):
        html = "<html><body>free public post</body></html>"
        self.assertFalse(
            is_probably_paid_substack(
                entry_title="Open note",
                entry_url="https://abc.substack.com/p/test",
                html=html,
            )
        )


if __name__ == "__main__":
    unittest.main()

