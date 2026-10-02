from django.test import SimpleTestCase
from django.urls import reverse


class DashboardOverviewTests(SimpleTestCase):
    def get_dashboard(self):
        return self.client.get(reverse("dashboard:overview"))

    def test_dashboard_url_resolves(self):
        self.assertEqual(reverse("dashboard:overview"), "/dashboard/")

    def test_dashboard_returns_http_200(self):
        self.assertEqual(self.get_dashboard().status_code, 200)

    def test_dashboard_uses_expected_overview_template(self):
        response = self.get_dashboard()
        self.assertTemplateUsed(response, "dashboard/overview.html")

    def test_brand_and_page_heading_render(self):
        response = self.get_dashboard()

        self.assertContains(response, "AegisPay")
        self.assertContains(response, "Risk Overview")

    def test_prototype_and_synthetic_labels_render(self):
        response = self.get_dashboard()

        self.assertContains(response, "Prototype dashboard")
        self.assertContains(response, "Synthetic demo data")

    def test_all_metric_card_labels_render(self):
        response = self.get_dashboard()

        for label in (
            "Transactions Analyzed",
            "Flagged / Review Queue",
            "Simulated Protected Value",
            "Intervention Rate",
        ):
            with self.subTest(label=label):
                self.assertContains(response, label)

    def test_main_navigation_labels_render(self):
        response = self.get_dashboard()

        for label in (
            "Overview",
            "Transactions",
            "Review Queue",
            "Network Intelligence",
            "Experiments",
            "Reports",
        ):
            with self.subTest(label=label):
                self.assertContains(response, label)

    def test_future_navigation_is_disabled(self):
        response = self.get_dashboard()

        self.assertContains(response, 'aria-disabled="true"')
        self.assertContains(response, "Soon")

    def test_main_landmark_is_accessible(self):
        response = self.get_dashboard()

        self.assertContains(response, 'id="main-content"')
        self.assertContains(response, 'role="main"')

    def test_review_capacity_section_renders_demo_values(self):
        response = self.get_dashboard()

        self.assertContains(response, "Human Review Capacity")
        self.assertContains(response, "14")
        self.assertContains(response, "/ 20")
        self.assertContains(response, "6 slots remaining")

    def test_recent_transactions_table_has_semantic_headers(self):
        response = self.get_dashboard()

        for header in ("Time", "Amount", "Risk", "Status", "Intervention"):
            with self.subTest(header=header):
                self.assertContains(response, f">{header}</th>")

    def test_dashboard_shell_references_expected_static_assets(self):
        response = self.get_dashboard()

        for asset in (
            "dashboard/css/tokens.css",
            "dashboard/css/base.css",
            "dashboard/css/components.css",
            "dashboard/css/dashboard.css",
            "dashboard/js/shell.js",
        ):
            with self.subTest(asset=asset):
                self.assertContains(response, asset)


class TransactionDetailTests(SimpleTestCase):
    def get_detail(self, transaction_id="TX-8420"):
        return self.client.get(
            reverse(
                "dashboard:transaction_detail",
                args=[transaction_id],
            )
        )

    def test_transaction_detail_url_resolves(self):
        self.assertEqual(
            reverse(
                "dashboard:transaction_detail",
                args=["TX-8420"],
            ),
            "/dashboard/transactions/TX-8420/",
        )

    def test_transaction_detail_returns_http_200(self):
        self.assertEqual(self.get_detail().status_code, 200)

    def test_transaction_detail_uses_expected_template(self):
        self.assertTemplateUsed(
            self.get_detail(),
            "dashboard/transaction_detail.html",
        )

    def test_transaction_id_and_risk_score_render(self):
        response = self.get_detail()
        self.assertContains(response, "TX-8420")
        self.assertContains(response, "0.85")
        self.assertContains(response, "CRITICAL")

    def test_risk_reason_text_renders(self):
        response = self.get_detail()
        self.assertContains(response, "recently changed devices")
        self.assertContains(response, "HIGH_RECIPIENT_FAN_IN")

    def test_behavioral_and_network_intelligence_render(self):
        response = self.get_detail()
        self.assertContains(response, "Behavioral Intelligence")
        self.assertContains(response, "Amount vs sender mean")
        self.assertContains(response, "Network Intelligence")
        self.assertContains(response, "Unique senders / 24h")

    def test_context_probe_question_and_answer_render(self):
        response = self.get_detail()
        self.assertContains(response, "Decision-Relevant Context Probe")
        self.assertContains(response, "Does the recipient or person guiding")
        self.assertContains(response, "claimed to represent a financial institution")
        self.assertContains(response, "Decision impact")

    def test_final_intervention_and_assumption_disclaimer_render(self):
        response = self.get_detail()
        self.assertContains(response, "Selected Intervention")
        self.assertContains(response, "HUMAN REVIEW")
        self.assertContains(response, "prototype decision assumptions")

    def test_no_probe_scenario_explains_why_context_was_not_required(self):
        response = self.get_detail("TX-12600")
        self.assertContains(response, "No probe required")
        self.assertContains(response, "already critical")

    def test_overview_links_to_demo_transaction_detail(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertContains(
            response,
            reverse(
                "dashboard:transaction_detail",
                args=["TX-8420"],
            ),
        )

    def test_unknown_demo_transaction_returns_404(self):
        self.assertEqual(
            self.get_detail("TX-unknown").status_code,
            404,
        )
