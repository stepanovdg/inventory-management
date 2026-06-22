"""
Tests for reports API endpoints (quarterly + monthly trends) and their filters.
"""
import pytest


class TestQuarterlyReportsEndpoint:
    """Test suite for GET /api/reports/quarterly."""

    def test_get_quarterly_reports(self, client):
        """Test getting quarterly performance reports."""
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first = data[0]
        for field in (
            "quarter", "total_orders", "total_revenue",
            "avg_order_value", "fulfillment_rate",
        ):
            assert field in first

    def test_quarterly_sorted_by_quarter(self, client):
        """Quarters should be returned in ascending order."""
        data = client.get("/api/reports/quarterly").json()
        quarters = [q["quarter"] for q in data]
        assert quarters == sorted(quarters)

    def test_quarterly_avg_order_value_calculation(self, client):
        """avg_order_value should equal total_revenue / total_orders."""
        data = client.get("/api/reports/quarterly").json()
        for q in data:
            if q["total_orders"] > 0:
                expected = q["total_revenue"] / q["total_orders"]
                assert abs(q["avg_order_value"] - expected) < 0.5

    def test_quarterly_fulfillment_rate_range(self, client):
        """Fulfillment rate should be a percentage between 0 and 100."""
        data = client.get("/api/reports/quarterly").json()
        for q in data:
            assert 0 <= q["fulfillment_rate"] <= 100

    def test_quarterly_respects_warehouse_filter(self, client):
        """Filtering by warehouse should not exceed the unfiltered totals."""
        all_data = client.get("/api/reports/quarterly").json()
        tokyo = client.get("/api/reports/quarterly?warehouse=Tokyo").json()

        all_orders = sum(q["total_orders"] for q in all_data)
        tokyo_orders = sum(q["total_orders"] for q in tokyo)
        assert tokyo_orders <= all_orders
        assert tokyo_orders > 0  # Tokyo has orders in the dataset

    def test_quarterly_respects_status_filter(self, client):
        """With status=Delivered, fulfillment rate should be 100% per quarter."""
        data = client.get("/api/reports/quarterly?status=Delivered").json()
        for q in data:
            assert q["fulfillment_rate"] == 100.0

    def test_quarterly_respects_month_filter(self, client):
        """Filtering by a single month should yield only that month's quarter."""
        data = client.get("/api/reports/quarterly?month=2025-01").json()
        # January falls in Q1-2025 only
        quarters = [q["quarter"] for q in data]
        assert quarters == ["Q1-2025"]


class TestMonthlyTrendsEndpoint:
    """Test suite for GET /api/reports/monthly-trends."""

    def test_get_monthly_trends(self, client):
        """Test getting month-over-month trends."""
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first = data[0]
        for field in ("month", "order_count", "revenue", "delivered_count"):
            assert field in first

    def test_monthly_sorted_by_month(self, client):
        """Months should be returned in ascending order."""
        data = client.get("/api/reports/monthly-trends").json()
        months = [m["month"] for m in data]
        assert months == sorted(months)

    def test_monthly_month_format(self, client):
        """Month field should be in YYYY-MM format."""
        data = client.get("/api/reports/monthly-trends").json()
        for m in data:
            assert len(m["month"]) == 7
            assert m["month"][:2] == "20"
            assert m["month"][4] == "-"

    def test_monthly_respects_month_filter(self, client):
        """Filtering by a single month should return only that month."""
        data = client.get("/api/reports/monthly-trends?month=2025-03").json()
        months = [m["month"] for m in data]
        assert months == ["2025-03"]

    def test_monthly_respects_category_filter(self, client):
        """Filtering by category should not exceed unfiltered order counts."""
        all_data = client.get("/api/reports/monthly-trends").json()
        sensors = client.get("/api/reports/monthly-trends?category=Sensors").json()

        all_orders = sum(m["order_count"] for m in all_data)
        sensors_orders = sum(m["order_count"] for m in sensors)
        assert sensors_orders <= all_orders

    def test_monthly_filter_all_is_noop(self, client):
        """Passing 'all' for filters should behave like no filter."""
        base = client.get("/api/reports/monthly-trends").json()
        with_all = client.get(
            "/api/reports/monthly-trends?warehouse=all&category=all&status=all&month=all"
        ).json()
        assert len(with_all) == len(base)
