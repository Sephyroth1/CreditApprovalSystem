from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Customer, Loan


class CheckEligibilityTests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Test",
            last_name="User",
            phone_number="9999999999",
            monthly_salary=50000,
            approved_limit=1000000,
            current_debt=0,
        )

    def test_high_score_no_correction(self):
        data = {
            "customer_id": self.customer.id,
            "loan_amount": 100000,
            "interest_rate": 15,
            "tenure": 12,
        }

        response = self.client.post("/api/check-eligibility/", data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["approval"])
        self.assertEqual(response.data["corrected_interest_rate"], 16)

    def test_emi_exceeds_salary(self):
        data = {
            "customer_id": self.customer.id,
            "loan_amount": 10000000,
            "interest_rate": 15,
            "tenure": 6,
        }

        response = self.client.post("/api/check-eligibility/", data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["approval"])
        self.assertEqual(response.data["message"], "EMI exceeds 50% of salary")

    def test_approved_limit_exceeded(self):
        data = {
            "customer_id": self.customer.id,
            "loan_amount": self.customer.approved_limit * 2,
            "interest_rate": 8,
            "tenure": 240,
        }

        response = self.client.post("/api/check-eligibility/", data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["approval"])
        self.assertEqual(response.data["message"], "Approved limit exceeded")
