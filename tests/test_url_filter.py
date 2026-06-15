"""Unit tests for utils/url_filter — pure URL/SERP helpers (no network)."""

import unittest

from utils.url_filter import (
    registered_domain,
    is_search_engine_url,
    looks_like_serp,
    cap_per_domain,
    is_bot_block,
)


class TestRegisteredDomain(unittest.TestCase):
    def test_strips_scheme_www_path_and_lowercases(self):
        self.assertEqual(registered_domain("https://www.Bing.com/path?q=1"), "bing.com")
        self.assertEqual(registered_domain("http://t.me/lolla_lamb15"), "t.me")
        self.assertEqual(registered_domain("https://html.duckduckgo.com/html/"), "html.duckduckgo.com")

    def test_garbage_input_is_safe(self):
        self.assertEqual(registered_domain(""), "")
        self.assertEqual(registered_domain(None), "")
        self.assertEqual(registered_domain("not a url"), "")


class TestIsSearchEngineUrl(unittest.TestCase):
    def test_search_engines_detected(self):
        for u in [
            "https://www.google.com/search?q=x",
            "https://yandex.com/search/?text=x",
            "https://html.duckduckgo.com/html/",
            "https://duckduckgo.com/?q=x",
            "https://search.brave.com/search?q=x",
            "https://www.mojeek.com/search?q=x",
            "https://www.bing.com/search?q=x",
            "https://www.perplexity.ai/search/new?q=x",
        ]:
            self.assertTrue(is_search_engine_url(u), u)

    def test_real_profiles_not_flagged(self):
        for u in [
            "https://t.me/lolla_lamb15",
            "https://lolchess.gg/profile/euw/lolla_lamb15",
            "https://instagram.com/x",
            "https://github.com/x",
            "",
        ]:
            self.assertFalse(is_search_engine_url(u), u)


class TestLooksLikeSerp(unittest.TestCase):
    def test_serp_body_detected(self):
        serp = "log in\nweb\nimages\nvideo\nmaps\nsearch results\ndid you mean\nsettings"
        self.assertTrue(looks_like_serp(serp))

    def test_profile_body_not_serp(self):
        profile = "download\nif you have telegram, you can contact @lolla_lamb15 right away.\nsend message"
        self.assertFalse(looks_like_serp(profile))


class TestCapPerDomain(unittest.TestCase):
    def test_caps_each_domain_preserving_order(self):
        urls = (
            [f"https://yandex.com/search/?text={i}" for i in range(10)]
            + ["https://t.me/lolla_lamb15", "https://lolchess.gg/profile/x"]
        )
        out = cap_per_domain(urls, n=2)
        yandex = [u for u in out if "yandex.com" in u]
        self.assertLessEqual(len(yandex), 2)
        self.assertIn("https://t.me/lolla_lamb15", out)
        self.assertIn("https://lolchess.gg/profile/x", out)
        # order preserved
        self.assertEqual(out, sorted(out, key=lambda u: urls.index(u)))


class TestIsBotBlock(unittest.TestCase):
    def test_google_sorry_detected(self):
        self.assertTrue(is_bot_block("https://www.google.com/sorry/index?continue=x", ""))

    def test_captcha_text_detected(self):
        self.assertTrue(is_bot_block("https://example.com/x", "Please verify you are not a robot"))

    def test_normal_page_not_blocked(self):
        self.assertFalse(is_bot_block("https://t.me/lolla_lamb15", "send message"))


if __name__ == "__main__":
    unittest.main()
