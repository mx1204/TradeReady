import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.tradeready.main import app
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
    def test_classification_preview_fills_hs_and_verifies_output(self):
        client = TestClient(app)
        response = client.post(
            "/api/classification-preview",
            json={
                "product_confirmed": True,
                "destination_country": "Malaysia",
                "product_facts": {
                    "category": "smartphone",
                    "label": "Apple iPhone 12",
                    "wireless": True,
                    "battery": True,
                    "mains_powered": False,
                    "confidence": 0.91,
                    "source": "openai_vision",
                    "confirmed": True,
                },
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["classification"]["hs6"], "8517.13")
        self.assertEqual(data["classification"]["local_code"], "8517130000")
        self.assertEqual(data["critic"]["status"], "pass")
        self.assertTrue(data["evidence_pack"])

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

    def test_chat_endpoint_answers_from_trade_context_without_network(self):
        client = TestClient(app)
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            response = client.post(
                "/api/chat",
                json={
                    "message": "Where does the HS code come from? quantity is 200 and unit value is 1600 SGD",
                    "destination_country": "Singapore",
                    "current_step": 2,
                    "product_facts": {
                        "category": "smartphone",
                        "label": "Apple iPhone 12",
                        "wireless": True,
                        "battery": True,
                        "mains_powered": False,
                        "confidence": 0.91,
                        "source": "openai_vision",
                        "confirmed": True,
                    },
                    "classification": {
                        "hs6": "8517.13",
                        "local_code": "85171300",
                    },
                    "critic": {
                        "status": "pass",
                        "issues": [],
                        "checks": ["HS classification has cached source evidence."],
                    },
                },
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["source"], "local_fallback")
        self.assertIn("8517.13", data["reply"])
        self.assertEqual(data["suggested_fields"]["quantity"], 200)
        self.assertEqual(data["suggested_fields"]["unitValue"], 1600.0)
        self.assertEqual(data["suggested_fields"]["currency"], "SGD")

    def test_chat_endpoint_extracts_seller_buyer_fields_for_confirmation(self):
        client = TestClient(app)
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            response = client.post(
                "/api/chat",
                json={
                    "message": "200 iphones SGD 1600 each shipping Malaysia to Singapore seller Jason buyer Nora invoice TR-001",
                    "destination_country": "Singapore",
                },
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["suggested_fields"]["quantity"], 200)
        self.assertEqual(data["suggested_fields"]["unitValue"], 1600.0)
        self.assertEqual(data["suggested_fields"]["currency"], "SGD")
        self.assertEqual(data["suggested_fields"]["originCountry"], "Malaysia")
        self.assertEqual(data["suggested_fields"]["sellerName"], "Jason")
        self.assertEqual(data["suggested_fields"]["consigneeName"], "Nora")
        self.assertEqual(data["suggested_fields"]["invoiceNumber"], "TR-001")

    def test_chat_endpoint_extracts_invoice_number_after_is(self):
        client = TestClient(app)
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            response = client.post(
                "/api/chat",
                json={
                    "message": 'I got 1000pcs of iphone 12, and the unit value is SGD1200, the invoice number is 123456, The seller is "Jason seller", Buyer is "Jason buyer"',
                    "destination_country": "Malaysia",
                },
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["suggested_fields"]["quantity"], 1000)
        self.assertEqual(data["suggested_fields"]["unitValue"], 1200.0)
        self.assertEqual(data["suggested_fields"]["invoiceNumber"], "123456")
        self.assertEqual(data["suggested_fields"]["sellerName"], "Jason seller")
        self.assertEqual(data["suggested_fields"]["consigneeName"], "Jason buyer")


if __name__ == "__main__":
    unittest.main()
