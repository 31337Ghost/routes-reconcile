import unittest

from main import managed_route_updates, plan_managed_route_updates


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

    def test_updates_gateway_for_route_missing_from_current_dns_results(self):
        route = {"comment": "openai:old.example", "gateway": "10.0.0.1"}

        self.assertEqual(
            managed_route_updates(route, None, "wg0"),
            {"gateway": "wg0"},
        )

    def test_does_not_rewrite_comment_for_route_missing_from_current_dns_results(self):
        route = {"comment": "openai:old.example", "gateway": "wg0"}

        self.assertEqual(
            managed_route_updates(route, None, "wg0"),
            {},
        )

    def test_updates_comment_and_gateway_together(self):
        route = {"comment": "openai:api.openai.com", "gateway": "10.0.0.1"}

        self.assertEqual(
            managed_route_updates(route, "openai:chatgpt.com", "wg0"),
            {"comment": "openai:chatgpt.com", "gateway": "wg0"},
        )

    def test_plan_includes_current_and_stale_managed_routes(self):
        routes = [
            {
                "id": "*1",
                "dst-address": "1.1.1.1/32",
                "comment": "openai:old-owner.example",
                "gateway": "10.0.0.1",
            },
            {
                "id": "*2",
                "dst-address": "2.2.2.2/32",
                "comment": "openai:stale.example",
                "gateway": "10.0.0.1",
            },
            {
                "id": "*3",
                "dst-address": "3.3.3.3/32",
                "comment": "openai:already-correct.example",
                "gateway": "wg0",
            },
        ]

        self.assertEqual(
            plan_managed_route_updates(
                routes,
                {"1.1.1.1/32": "openai:current.example"},
                "wg0",
            ),
            [
                (
                    "*1",
                    {"comment": "openai:current.example", "gateway": "wg0"},
                ),
                ("*2", {"gateway": "wg0"}),
            ],
        )


if __name__ == "__main__":
    unittest.main()
