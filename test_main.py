import unittest

from main import managed_route_updates


class ManagedRouteUpdatesTest(unittest.TestCase):
    def test_returns_no_updates_when_route_matches(self):
        route = {"comment": "openai:chatgpt.com", "gateway": "wg0"}

        self.assertEqual(
            managed_route_updates(route, "openai:chatgpt.com", "wg0"),
            {},
        )

    def test_updates_gateway_without_rewriting_matching_comment(self):
        route = {"comment": "openai:chatgpt.com", "gateway": "10.0.0.1"}

        self.assertEqual(
            managed_route_updates(route, "openai:chatgpt.com", "wg0"),
            {"gateway": "wg0"},
        )

    def test_updates_comment_and_gateway_together(self):
        route = {"comment": "openai:api.openai.com", "gateway": "10.0.0.1"}

        self.assertEqual(
            managed_route_updates(route, "openai:chatgpt.com", "wg0"),
            {"comment": "openai:chatgpt.com", "gateway": "wg0"},
        )


if __name__ == "__main__":
    unittest.main()
