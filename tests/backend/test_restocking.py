"""
Tests for restocking API endpoints (candidates + submitted orders).
"""
from datetime import date

import pytest


TREND_PRIORITY = {"increasing": 0, "stable": 1, "decreasing": 2}
CATEGORY_LEAD_TIME = {
    "Power Supplies": 12,
    "Sensors": 14,
    "Controllers": 16,
    "Actuators": 18,
    "Components": 20,
}
DEFAULT_LEAD_TIME = 20


class TestRestockCandidatesEndpoint:
    """Test suite for GET /api/restocking/candidates."""

    def test_get_all_candidates(self, client):
        """Test getting all restock candidates."""
        response = client.get("/api/restocking/candidates")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 9  # one per demand forecast record

        first = data[0]
        for field in (
            "item_sku", "item_name", "category", "current_demand",
            "forecasted_demand", "trend", "recommended_quantity",
            "unit_cost", "line_cost", "lead_time_days",
        ):
            assert field in first

    def test_candidate_field_types(self, client):
        """Test that candidate numeric fields have proper types."""
        data = client.get("/api/restocking/candidates").json()
        for c in data:
            assert isinstance(c["recommended_quantity"], int)
            assert isinstance(c["current_demand"], int)
            assert isinstance(c["forecasted_demand"], int)
            assert isinstance(c["unit_cost"], (int, float))
            assert isinstance(c["line_cost"], (int, float))
            assert isinstance(c["lead_time_days"], int)
            assert c["unit_cost"] >= 0
            assert c["line_cost"] >= 0
            assert c["lead_time_days"] > 0

    def test_recommended_quantity_equals_forecast(self, client):
        """Recommended quantity should equal the forecasted demand."""
        data = client.get("/api/restocking/candidates").json()
        for c in data:
            assert c["recommended_quantity"] == c["forecasted_demand"]

    def test_line_cost_calculation(self, client):
        """Line cost should equal recommended_quantity * unit_cost."""
        data = client.get("/api/restocking/candidates").json()
        for c in data:
            expected = c["recommended_quantity"] * c["unit_cost"]
            assert abs(c["line_cost"] - expected) < 0.01

    def test_lead_time_matches_category(self, client):
        """Lead time should be derived from the item category map."""
        data = client.get("/api/restocking/candidates").json()
        for c in data:
            expected = CATEGORY_LEAD_TIME.get(c["category"], DEFAULT_LEAD_TIME)
            assert c["lead_time_days"] == expected

    def test_candidates_sorted_by_trend_then_line_cost(self, client):
        """Candidates should be sorted by trend priority, then line_cost desc."""
        data = client.get("/api/restocking/candidates").json()
        keys = [
            (TREND_PRIORITY.get(c["trend"], 1), -c["line_cost"])
            for c in data
        ]
        assert keys == sorted(keys)

    def test_trend_values_are_valid(self, client):
        """Trend should be one of the known values."""
        data = client.get("/api/restocking/candidates").json()
        for c in data:
            assert c["trend"] in ("increasing", "stable", "decreasing")


class TestSubmittedOrdersEndpoint:
    """Test suite for POST/GET /api/restocking/orders."""

    def _sample_payload(self):
        return {
            "budget": 15000,
            "items": [
                {
                    "item_sku": "FLT-405",
                    "item_name": "Oil Filter Cartridge",
                    "quantity": 950,
                    "unit_cost": 6.25,
                    "lead_time_days": 20,
                },
                {
                    "item_sku": "SNR-420",
                    "item_name": "Temperature Sensor Module",
                    "quantity": 182,
                    "unit_cost": 89.50,
                    "lead_time_days": 14,
                },
            ],
        }

    def test_create_restock_order(self, client):
        """Test submitting a restock order returns a well-formed order."""
        payload = self._sample_payload()
        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["status"] == "Submitted"
        assert order["order_number"].startswith("RST-")
        assert len(order["items"]) == 2
        assert order["budget"] == payload["budget"]

    def test_total_value_calculation(self, client):
        """total_value should equal sum(quantity * unit_cost)."""
        payload = self._sample_payload()
        order = client.post("/api/restocking/orders", json=payload).json()
        expected = sum(i["quantity"] * i["unit_cost"] for i in payload["items"])
        assert abs(order["total_value"] - expected) < 0.01

    def test_max_lead_time_and_expected_delivery(self, client):
        """max_lead_time_days = max line lead time; expected delivery offset matches."""
        payload = self._sample_payload()
        order = client.post("/api/restocking/orders", json=payload).json()

        expected_max = max(i["lead_time_days"] for i in payload["items"])
        assert order["max_lead_time_days"] == expected_max

        order_date = date.fromisoformat(order["order_date"])
        expected_delivery = date.fromisoformat(order["expected_delivery"])
        assert (expected_delivery - order_date).days == expected_max

    def test_submitted_order_appears_in_list(self, client):
        """A submitted order should appear in GET /api/restocking/orders."""
        before = client.get("/api/restocking/orders").json()
        created = client.post(
            "/api/restocking/orders", json=self._sample_payload()
        ).json()

        after = client.get("/api/restocking/orders").json()
        assert isinstance(after, list)
        assert len(after) == len(before) + 1

        order_numbers = [o["order_number"] for o in after]
        assert created["order_number"] in order_numbers

    def test_create_restock_order_empty_items_returns_400(self, client):
        """An order with no items should be rejected with 400."""
        response = client.post(
            "/api/restocking/orders", json={"budget": 1000, "items": []}
        )
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_create_restock_order_invalid_payload_returns_422(self, client):
        """A malformed line item should fail Pydantic validation (422)."""
        bad = {"budget": 1000, "items": [{"item_sku": "X"}]}  # missing fields
        response = client.post("/api/restocking/orders", json=bad)
        assert response.status_code == 422

    def test_get_submitted_orders_structure(self, client):
        """Submitted orders list items should have the expected structure."""
        client.post("/api/restocking/orders", json=self._sample_payload())
        data = client.get("/api/restocking/orders").json()
        assert isinstance(data, list)
        assert len(data) > 0

        order = data[0]
        for field in (
            "id", "order_number", "order_date", "expected_delivery",
            "status", "items", "total_value", "max_lead_time_days", "budget",
        ):
            assert field in order
