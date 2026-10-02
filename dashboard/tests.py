from django.test import SimpleTestCase
from django.urls import reverse

from core.contracts import ScamContext
from dashboard.presenters.payment_demo import context_for_answer
from dashboard.presenters.network_intelligence import present_network

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


class CustomerPaymentDemoTests(SimpleTestCase):
    def payment_url(self, name="dashboard:payment_demo"):
        return reverse(name)

    def payment_data(self, scenario="normal"):
        return {
            "scenario": scenario,
            "recipient": "Ali Khan",
            "amount": "5000.00",
            "note": "Rent payment",
        }

    def test_payment_demo_route_and_template_render(self):
        response = self.client.get(self.payment_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/customer/payment.html",
        )
        self.assertContains(response, "Prototype Demo Controls")
        self.assertContains(response, "No real money is transferred")

    def test_payment_demo_url_resolves(self):
        self.assertEqual(
            self.payment_url(),
            "/dashboard/demo/payment/",
        )

    def test_invalid_amount_is_rejected(self):
        data = self.payment_data()
        data["amount"] = "0"

        response = self.client.post(self.payment_url(), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ensure this value is greater than or equal to")

    def test_unknown_scenario_is_rejected(self):
        response = self.client.post(
            self.payment_url(),
            self.payment_data("unknown"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")

    def test_normal_scenario_reaches_allow_without_probe(self):
        response = self.client.post(
            self.payment_url(),
            self.payment_data(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/customer/intervention.html",
        )
        self.assertContains(response, "Ready to continue")
        self.assertContains(response, "No additional security check is required")
        self.assertNotContains(response, "Risk score")

    def test_normal_confirmation_renders_simulated_success(self):
        response = self.client.post(
            reverse("dashboard:payment_demo_success"),
            self.payment_data(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/customer/success.html",
        )
        self.assertContains(response, "Payment Demo Complete")
        self.assertContains(response, "No real money was transferred")

    def test_guided_scenario_renders_exact_runtime_question(self):
        response = self.client.post(
            self.payment_url(),
            self.payment_data("guided"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/customer/context_probe.html",
        )
        self.assertContains(response, "Does the recipient or person guiding")
        self.assertContains(response, "financial institution?")

    def test_guided_yes_recomputes_to_human_review(self):
        data = self.payment_data("guided")
        data.update(
            {
                "answer_key": "support_impersonation",
                "answer": "yes",
            }
        )

        response = self.client.post(
            reverse("dashboard:payment_demo_context"),
            data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Additional review recommended")
        self.assertContains(response, "AegisPay recommends human review")

    def test_guided_no_recomputes_to_verify_without_fake_risk_reduction(self):
        data = self.payment_data("guided")
        data.update(
            {
                "answer_key": "support_impersonation",
                "answer": "no",
            }
        )

        response = self.client.post(
            reverse("dashboard:payment_demo_context"),
            data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please verify before continuing")
        self.assertNotContains(response, "Additional review recommended")

    def test_context_answer_populates_only_selected_field(self):
        context = context_for_answer("support_impersonation", "yes")

        self.assertEqual(context.support_impersonation, True)
        for field in ScamContext.__dataclass_fields__:
            if field != "support_impersonation":
                self.assertIsNone(getattr(context, field))

    def test_inconsistent_context_question_fails_safely(self):
        data = self.payment_data("guided")
        data.update(
            {
                "answer_key": "phone_call",
                "answer": "yes",
            }
        )

        response = self.client.post(
            reverse("dashboard:payment_demo_context"),
            data,
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "does not belong to the selected payment",
            status_code=400,
        )

    def test_strong_evidence_skips_probe_and_recommends_review(self):
        response = self.client.post(
            self.payment_url(),
            self.payment_data("strong"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Additional review recommended")
        self.assertNotContains(response, "Security check")

    def test_invalid_flow_state_does_not_execute_payment(self):
        response = self.client.get(
            reverse("dashboard:payment_demo_result")
        )

        self.assertEqual(response.status_code, 404)


class NetworkIntelligenceTests(SimpleTestCase):
    def get_network(self, scenario=None):
        url = reverse("dashboard:network_intelligence")
        if scenario:
            url += f"?scenario={scenario}"
        return self.client.get(url)

    def test_network_route_and_template_render(self):
        response = self.get_network()

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/network_intelligence.html",
        )
        self.assertContains(response, "Synthetic network demo")

    def test_default_and_alternate_scenarios_render(self):
        self.assertContains(self.get_network(), "WLT-FOCAL")
        self.assertContains(
            self.get_network("concentrated"),
            "WLT-ALPHA",
        )

    def test_invalid_scenario_falls_back_safely(self):
        response = self.get_network("not-a-scenario")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WLT-FOCAL")

    def test_canonical_network_metrics_render(self):
        response = self.get_network()

        for label in (
            "Unique senders 24h",
            "Fan-in 24h",
            "Fan-out 24h",
            "Pass-through ratio",
            "Cash-out velocity 1h",
        ):
            with self.subTest(label=label):
                self.assertContains(response, label)

    def test_high_risk_explanation_and_disclaimer_render(self):
        response = self.get_network()

        self.assertContains(response, "These indicators increase network-related concern")
        self.assertContains(response, "do not prove that the wallet is fraudulent")
        self.assertContains(response, "HIGH_RECIPIENT_FAN_IN")
        self.assertContains(response, "HIGH_PASS_THROUGH")
        self.assertContains(response, "RAPID_CASHOUT")

    def test_concentrated_scenario_does_not_claim_safe(self):
        response = self.get_network("concentrated")

        self.assertContains(response, "lower network concern")
        self.assertContains(response, "not a claim that the wallet is safe")
        self.assertContains(response, "not a claim that the wallet is safe")

    def test_event_table_graph_payload_and_assets_render(self):
        response = self.get_network()

        self.assertContains(response, "Representative Transaction Flow")
        self.assertContains(response, 'id="network-graph-data"')
        self.assertContains(response, "dashboard/js/network_graph.js")
        self.assertContains(response, "dashboard/css/dashboard.css")

    def test_sidebar_network_item_is_active(self):
        response = self.get_network()

        self.assertContains(
            response,
            'href="/dashboard/network/" aria-current="page"',
        )
        self.assertNotContains(
            response,
            'href="/dashboard/" aria-current="page"',
        )

    def test_presenter_is_deterministic_and_metrics_match_events(self):
        first = present_network("high-risk")
        second = present_network("high-risk")

        self.assertEqual(first["graph"], second["graph"])
        self.assertEqual(first["metrics"]["fan_in"], 24)
        self.assertEqual(first["metrics"]["fan_out"], 13)
        self.assertEqual(first["metrics"]["unique_senders"], 8)
        self.assertEqual(first["metrics"]["pass_through_ratio"], 0.86)
        self.assertEqual(first["metrics"]["cashout_velocity"], 0.78)
        self.assertEqual(
            first["metrics"]["fan_in"],
            sum(
                event.recipient == first["scenario"].focal_wallet
                for event in first["events"]
            ),
        )

    def test_transaction_detail_network_link_is_functional_for_supported_demo(self):
        response = self.client.get(
            reverse(
                "dashboard:transaction_detail",
                args=["TX-8420"],
            )
        )

        self.assertContains(
            response,
            reverse("dashboard:network_intelligence") + "?scenario=high-risk",
        )
