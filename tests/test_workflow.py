import unittest

from backend.tradeready.models import CompliancePackage, ComplianceRunRequest, ProductFacts
from backend.tradeready.orchestrator import build_compliance_package, create_compliance_run, switch_destination
from backend.tradeready.vision import identify_from_text


def product(category: str, wireless: bool, battery: bool, mains_powered: bool = False) -> ProductFacts:
    return ProductFacts(
        category=category,
        label=category.replace("_", " ").title(),
        wireless=wireless,
        battery=battery,
        mains_powered=mains_powered,
        confidence=0.91,
        confirmed=True,
    )


class WorkflowTests(unittest.TestCase):
    def test_fallback_identifies_all_supported_demo_categories(self):
        cases = {
            "wireless earbuds photo.jpg": "wireless_earbuds",
            "portable bluetooth speaker.png": "bluetooth_speaker",
            "smartwatch.webp": "smartwatch",
            "phone charger adapter.jpg": "phone_charger",
            "navy blue iphone 12 smartphone.png": "smartphone",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                result = identify_from_text(text)
                self.assertEqual(result.detected_category, expected)
                self.assertTrue(result.confirmation_required)

    def test_requires_user_confirmation_before_compliance_output(self):
        request = ComplianceRunRequest(
            product_facts=product("wireless_earbuds", True, True).model_copy(update={"confirmed": False}),
            product_confirmed=False,
            destination_country="Malaysia",
            shipment_text="200 units wireless earbuds, SGD 45 each, shipping Singapore to Malaysia",
        )
        result = build_compliance_package(request, run_id="demo")
        self.assertEqual(result.workflow_status, "needs_user_input")
        self.assertIn("product_confirmation", result.missing_fields)

    def test_missing_value_returns_needs_user_input(self):
        request = ComplianceRunRequest(
            product_facts=product("bluetooth_speaker", True, True),
            product_confirmed=True,
            destination_country="Malaysia",
            shipment_text="200 units bluetooth speaker, shipping Singapore to Malaysia",
        )
        result = build_compliance_package(request, run_id="demo")
        self.assertEqual(result.workflow_status, "needs_user_input")
        self.assertIn("unit_value", result.missing_fields)

    def test_wireless_earbuds_malaysia_generates_validated_package(self):
        request = ComplianceRunRequest(
            product_facts=product("wireless_earbuds", True, True),
            product_confirmed=True,
            destination_country="Malaysia",
            shipment_text="200 units wireless earbuds, SGD 45 each, shipping Singapore to Malaysia, invoice TR-001",
        )
        result = build_compliance_package(request, run_id="demo")
        self.assertIsInstance(result, CompliancePackage)
        self.assertEqual(result.critic.status, "pass")
        self.assertEqual(result.classification.hs6, "8518.30")
        self.assertEqual(result.duty_tax.customs_value, 9000.0)
        self.assertEqual(result.duty_tax.taxes[0].amount, 900.0)
        self.assertEqual(result.auto_filled_fields.fields["invoice_number"], "TR-001")
        self.assertIn("SIRIM QAS", result.restricted_goods.certification_bodies)
        self.assertTrue(result.evidence_pack)

    def test_switch_destination_returns_diff(self):
        request = ComplianceRunRequest(
            product_facts=product("smartwatch", True, True),
            product_confirmed=True,
            destination_country="Malaysia",
            shipment_text="50 units smartwatch, SGD 120 each, shipping Malaysia to Singapore",
        )
        first = create_compliance_run(request)
        self.assertIsInstance(first, CompliancePackage)
        switched = switch_destination(first.run_id, "Singapore")
        self.assertIsInstance(switched, CompliancePackage)
        self.assertIsNotNone(switched.jurisdiction_diff)
        self.assertEqual(switched.jurisdiction_diff["to"], "Singapore")
        self.assertNotEqual(
            switched.jurisdiction_diff["duty_tax"]["old_tax"][0]["rate"],
            switched.jurisdiction_diff["duty_tax"]["new_tax"][0]["rate"],
        )

    def test_smartphone_malaysia_generates_validated_package(self):
        request = ComplianceRunRequest(
            product_facts=product("smartphone", True, True),
            product_confirmed=True,
            destination_country="Malaysia",
            shipment_text="10 units Navy Blue iPhone 12, SGD 500 each, shipping Singapore to Malaysia",
        )
        result = build_compliance_package(request, run_id="demo")
        self.assertIsInstance(result, CompliancePackage)
        self.assertEqual(result.classification.hs6, "8517.13")
        self.assertIn("SIRIM QAS", result.restricted_goods.certification_bodies)


if __name__ == "__main__":
    unittest.main()
