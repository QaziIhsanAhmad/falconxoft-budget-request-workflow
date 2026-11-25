
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError

from apps.budget_requests.models import BudgetRequest
from apps.budget_requests.services.budget_requests import (
    create_budget_request,
)


User = get_user_model()


class CreateBudgetRequestTest(TestCase):

    def setUp(self):
        self.client_group = Group.objects.create(name="Client")
        self.manager_group = Group.objects.create(name="Manager")

        self.client_user = User.objects.create_user(
            username="client_user",
            password="testpass123"
        )
        self.client_user.groups.add(self.client_group)

        self.manager_user = User.objects.create_user(
            username="manager_user",
            password="testpass123"
        )
        self.manager_user.groups.add(self.manager_group)

        self.valid_data = {
            "title": "Office Equipment",
            "amount": Decimal("5000.00"),
            "justification": "Required for office operations.",
        }

    def test_client_can_create_budget_request(self):
        budget_request = create_budget_request(
            self.client_user,
            self.valid_data
        )

        self.assertIsInstance(budget_request, BudgetRequest)
        self.assertTrue(
            BudgetRequest.objects.filter(pk=budget_request.pk).exists()
        )

    def test_created_request_has_pending_status(self):
        budget_request = create_budget_request(
            self.client_user,
            self.valid_data
        )

        self.assertEqual(budget_request.status, "PENDING")

    def test_requester_is_logged_in_client(self):
        budget_request = create_budget_request(
            self.client_user,
            self.valid_data
        )

        self.assertEqual(budget_request.requester, self.client_user)

    def test_manager_cannot_create_budget_request(self):
        with self.assertRaises(PermissionDenied):
            create_budget_request(
                self.manager_user,
                self.valid_data
            )

    def test_unauthenticated_user_cannot_create_request(self):
        with self.assertRaises(PermissionDenied):
            create_budget_request(
                AnonymousUser(),
                self.valid_data
            )

    def test_extra_and_missing_fields_are_rejected(self):
        extra_data = {
            **self.valid_data,
            "status": "APPROVED",
        }

        missing_data = {
            "title": "Office Equipment",
            "amount": Decimal("5000.00"),
        }

        with self.assertRaises(ValidationError):
            create_budget_request(
                self.client_user,
                extra_data
            )

        with self.assertRaises(ValidationError):
            create_budget_request(
                self.client_user,
                missing_data
            )

    def test_zero_and_negative_amount_are_rejected(self):
        for amount in [Decimal("0.00"), Decimal("-100.00")]:
            with self.subTest(amount=amount):
                invalid_data = {
                    **self.valid_data,
                    "amount": amount,
                }

                with self.assertRaises(ValidationError):
                    create_budget_request(
                        self.client_user,
                        invalid_data
                    )

    def test_whitespace_only_title_is_rejected(self):
        invalid_data = {
            **self.valid_data,
            "title": "     ",
        }

        with self.assertRaises(ValidationError):
            create_budget_request(
                self.client_user,
                invalid_data
            )

    def test_whitespace_only_justification_is_rejected(self):
        invalid_data = {
            **self.valid_data,
            "justification": "     ",
        }

        with self.assertRaises(ValidationError):
            create_budget_request(
                self.client_user,
                invalid_data
            )
