from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError

from apps.budget_requests.models import BudgetRequest
from apps.budget_requests.services.budget_requests import (
    create_budget_request,
    update_budget_request,
    withdraw_budget_request,
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
            self.client_user, self.valid_data
        )
        self.assertIsInstance(budget_request, BudgetRequest)
        self.assertTrue(
            BudgetRequest.objects.filter(pk=budget_request.pk).exists()
        )

    def test_created_request_has_pending_status(self):
        budget_request = create_budget_request(
            self.client_user, self.valid_data
        )
        self.assertEqual(budget_request.status, "PENDING")

    def test_requester_is_logged_in_client(self):
        budget_request = create_budget_request(
            self.client_user, self.valid_data
        )
        self.assertEqual(budget_request.requester, self.client_user)

    def test_manager_cannot_create_budget_request(self):
        with self.assertRaises(PermissionDenied):
            create_budget_request(self.manager_user, self.valid_data)

    def test_unauthenticated_user_cannot_create_request(self):
        with self.assertRaises(PermissionDenied):
            create_budget_request(AnonymousUser(), self.valid_data)

    def test_extra_and_missing_fields_are_rejected(self):
        extra_data = {**self.valid_data, "status": "APPROVED"}
        missing_data = {
            "title": "Office Equipment",
            "amount": Decimal("5000.00"),
        }

        with self.assertRaises(ValidationError):
            create_budget_request(self.client_user, extra_data)

        with self.assertRaises(ValidationError):
            create_budget_request(self.client_user, missing_data)

    def test_zero_and_negative_amount_are_rejected(self):
        for amount in [Decimal("0.00"), Decimal("-100.00")]:
            with self.subTest(amount=amount):
                invalid_data = {**self.valid_data, "amount": amount}
                with self.assertRaises(ValidationError):
                    create_budget_request(self.client_user, invalid_data)

    def test_whitespace_only_title_is_rejected(self):
        invalid_data = {**self.valid_data, "title": "     "}
        with self.assertRaises(ValidationError):
            create_budget_request(self.client_user, invalid_data)

    def test_whitespace_only_justification_is_rejected(self):
        invalid_data = {**self.valid_data, "justification": "     "}
        with self.assertRaises(ValidationError):
            create_budget_request(self.client_user, invalid_data)


class BudgetRequestServiceBaseTest(TestCase):

    def setUp(self):
        self.client_group = Group.objects.create(name="Client")
        self.manager_group = Group.objects.create(name="Manager")
        self.admin_group = Group.objects.create(name="Admin")

        self.client_user = User.objects.create_user(
            username="owner_client",
            password="testpass123"
        )
        self.client_user.groups.add(self.client_group)

        self.other_client = User.objects.create_user(
            username="other_client",
            password="testpass123"
        )
        self.other_client.groups.add(self.client_group)

        self.manager_user = User.objects.create_user(
            username="manager_user",
            password="testpass123"
        )
        self.manager_user.groups.add(self.manager_group)

        self.admin_user = User.objects.create_user(
            username="admin_user",
            password="testpass123"
        )
        self.admin_user.groups.add(self.admin_group)

        self.budget_request = BudgetRequest.objects.create(
            title="Office Equipment",
            amount=Decimal("5000.00"),
            justification="Required for office operations.",
            requester=self.client_user,
        )


class UpdateBudgetRequestTest(BudgetRequestServiceBaseTest):

    def test_owner_client_can_update_pending_request(self):
        result = update_budget_request(
            self.client_user,
            self.budget_request.pk,
            {"title": "Updated Equipment"}
        )
        self.assertEqual(result.title, "Updated Equipment")

    def test_updated_values_are_saved_in_database(self):
        update_budget_request(
            self.client_user,
            self.budget_request.pk,
            {
                "title": "New Equipment",
                "amount": Decimal("7500.00"),
                "justification": "New business requirement.",
            }
        )

        self.budget_request.refresh_from_db()
        self.assertEqual(self.budget_request.title, "New Equipment")
        self.assertEqual(self.budget_request.amount, Decimal("7500.00"))
        self.assertEqual(
            self.budget_request.justification,
            "New business requirement."
        )

    def test_other_client_cannot_edit_request(self):
        with self.assertRaises(PermissionDenied):
            update_budget_request(
                self.other_client,
                self.budget_request.pk,
                {"title": "Unauthorized"}
            )

    def test_manager_cannot_edit_request(self):
        with self.assertRaises(PermissionDenied):
            update_budget_request(
                self.manager_user,
                self.budget_request.pk,
                {"title": "Manager Update"}
            )

    def test_admin_cannot_edit_request(self):
        with self.assertRaises(PermissionDenied):
            update_budget_request(
                self.admin_user,
                self.budget_request.pk,
                {"title": "Admin Update"}
            )

    def test_unauthenticated_user_cannot_edit_request(self):
        with self.assertRaises(PermissionDenied):
            update_budget_request(
                AnonymousUser(),
                self.budget_request.pk,
                {"title": "Unauthorized"}
            )

    def test_non_pending_request_cannot_be_edited(self):
        for status in ["APPROVED", "REJECTED", "WITHDRAWN"]:
            with self.subTest(status=status):
                BudgetRequest.objects.filter(
                    pk=self.budget_request.pk
                ).update(status=status)

                with self.assertRaises(PermissionDenied):
                    update_budget_request(
                        self.client_user,
                        self.budget_request.pk,
                        {"title": "Unauthorized"}
                    )

    def test_protected_fields_cannot_be_updated(self):
        with self.assertRaises(ValidationError):
            update_budget_request(
                self.client_user,
                self.budget_request.pk,
                {"status": "APPROVED"}
            )

    def test_empty_update_is_rejected(self):
        with self.assertRaises(ValidationError):
            update_budget_request(
                self.client_user,
                self.budget_request.pk,
                {}
            )

    def test_invalid_amount_is_rejected(self):
        for amount in [Decimal("0.00"), Decimal("-100.00")]:
            with self.subTest(amount=amount):
                with self.assertRaises(ValidationError):
                    update_budget_request(
                        self.client_user,
                        self.budget_request.pk,
                        {"amount": amount}
                    )

    def test_whitespace_only_title_is_rejected(self):
        with self.assertRaises(ValidationError):
            update_budget_request(
                self.client_user,
                self.budget_request.pk,
                {"title": "     "}
            )

    def test_whitespace_only_justification_is_rejected(self):
        with self.assertRaises(ValidationError):
            update_budget_request(
                self.client_user,
                self.budget_request.pk,
                {"justification": "     "}
            )

    def test_nonexistent_request_is_rejected(self):
        with self.assertRaises(ValidationError):
            update_budget_request(
                self.client_user,
                999999,
                {"title": "Not Found"}
            )


class WithdrawBudgetRequestTest(BudgetRequestServiceBaseTest):

    def test_owner_client_can_withdraw_pending_request(self):
        result = withdraw_budget_request(
            self.client_user, self.budget_request.pk
        )
        self.assertEqual(result.status, "WITHDRAWN")

    def test_withdrawn_request_is_retained_in_database(self):
        request_id = self.budget_request.pk

        withdraw_budget_request(self.client_user, request_id)

        self.assertTrue(
            BudgetRequest.objects.filter(pk=request_id).exists()
        )

    def test_original_fields_remain_unchanged_after_withdrawal(self):
        original = {
            "title": self.budget_request.title,
            "amount": self.budget_request.amount,
            "justification": self.budget_request.justification,
            "requester_id": self.budget_request.requester_id,
        }

        withdraw_budget_request(
            self.client_user, self.budget_request.pk
        )

        self.budget_request.refresh_from_db()

        self.assertEqual(self.budget_request.status, "WITHDRAWN")
        self.assertEqual(self.budget_request.title, original["title"])
        self.assertEqual(self.budget_request.amount, original["amount"])
        self.assertEqual(
            self.budget_request.justification,
            original["justification"]
        )
        self.assertEqual(
            self.budget_request.requester_id,
            original["requester_id"]
        )

    def test_other_client_cannot_withdraw_request(self):
        with self.assertRaises(PermissionDenied):
            withdraw_budget_request(
                self.other_client, self.budget_request.pk
            )

    def test_manager_cannot_withdraw_request(self):
        with self.assertRaises(PermissionDenied):
            withdraw_budget_request(
                self.manager_user, self.budget_request.pk
            )

    def test_admin_cannot_withdraw_request(self):
        with self.assertRaises(PermissionDenied):
            withdraw_budget_request(
                self.admin_user, self.budget_request.pk
            )

    def test_unauthenticated_user_cannot_withdraw_request(self):
        with self.assertRaises(PermissionDenied):
            withdraw_budget_request(
                AnonymousUser(), self.budget_request.pk
            )

    def test_non_pending_request_cannot_be_withdrawn(self):
        for status in ["APPROVED", "REJECTED", "WITHDRAWN"]:
            with self.subTest(status=status):
                BudgetRequest.objects.filter(
                    pk=self.budget_request.pk
                ).update(status=status)

                with self.assertRaises(PermissionDenied):
                    withdraw_budget_request(
                        self.client_user, self.budget_request.pk
                    )

    def test_withdrawn_request_cannot_be_edited_again(self):
        request_id = self.budget_request.pk
        withdraw_budget_request(self.client_user, request_id)

        with self.assertRaises(PermissionDenied):
            update_budget_request(
                self.client_user,
                request_id,
                {"title": "Changed after withdrawal"}
            )

    def test_withdrawn_request_cannot_be_withdrawn_again(self):
        request_id = self.budget_request.pk
        withdraw_budget_request(self.client_user, request_id)

        with self.assertRaises(PermissionDenied):
            withdraw_budget_request(self.client_user, request_id)

    def test_nonexistent_request_cannot_be_withdrawn(self):
        with self.assertRaises(ValidationError):
            withdraw_budget_request(self.client_user, 999999)


class ReviewBudgetRequestTest(BudgetRequestServiceBaseTest):

    def test_manager_can_approve_request(self):
        result = review_budget_request(
            self.manager_user,
            self.budget_request.pk,
            "APPROVED",
        )

        self.budget_request.refresh_from_db()

        self.assertEqual(result.status, "APPROVED")
        self.assertEqual(self.budget_request.status, "APPROVED")
        self.assertEqual(
            self.budget_request.reviewer,
            self.manager_user,
        )
        self.assertEqual(self.budget_request.reviewer_feedback, "")

    def test_manager_can_reject_request_with_feedback(self):
        feedback = "The requested amount is not justified."

        result = review_budget_request(
            self.manager_user,
            self.budget_request.pk,
            "REJECTED",
            feedback,
        )

        self.budget_request.refresh_from_db()

        self.assertEqual(result.status, "REJECTED")
        self.assertEqual(self.budget_request.status, "REJECTED")
        self.assertEqual(
            self.budget_request.reviewer,
            self.manager_user,
        )
        self.assertEqual(
            self.budget_request.reviewer_feedback,
            feedback,
        )

    def test_rejection_with_blank_feedback_is_denied(self):
        with self.assertRaises(ValidationError):
            review_budget_request(
                self.manager_user,
                self.budget_request.pk,
                "REJECTED",
                "",
            )

        self.budget_request.refresh_from_db()

        self.assertEqual(self.budget_request.status, "PENDING")
        self.assertIsNone(self.budget_request.reviewer)
        self.assertEqual(self.budget_request.reviewer_feedback, "")

    def test_rejection_with_whitespace_feedback_is_denied(self):
        with self.assertRaises(ValidationError):
            review_budget_request(
                self.manager_user,
                self.budget_request.pk,
                "REJECTED",
                "     ",
            )

        self.budget_request.refresh_from_db()

        self.assertEqual(self.budget_request.status, "PENDING")
        self.assertIsNone(self.budget_request.reviewer)
        self.assertEqual(self.budget_request.reviewer_feedback, "")

    def test_admin_cannot_review_request(self):
        with self.assertRaises(PermissionDenied):
            review_budget_request(
                self.admin_user,
                self.budget_request.pk,
                "APPROVED",
            )

        self.budget_request.refresh_from_db()

        self.assertEqual(self.budget_request.status, "PENDING")
        self.assertIsNone(self.budget_request.reviewer)
        self.assertEqual(self.budget_request.reviewer_feedback, "")

    def test_client_cannot_review_request(self):
        with self.assertRaises(PermissionDenied):
            review_budget_request(
                self.client_user,
                self.budget_request.pk,
                "APPROVED",
            )

        self.budget_request.refresh_from_db()

        self.assertEqual(self.budget_request.status, "PENDING")
        self.assertIsNone(self.budget_request.reviewer)
        self.assertEqual(self.budget_request.reviewer_feedback, "")

    def test_final_and_withdrawn_requests_cannot_be_reviewed_again(self):
        for status in ["APPROVED", "REJECTED", "WITHDRAWN"]:
            with self.subTest(status=status):
                self.budget_request.status = status
                self.budget_request.reviewer = None
                self.budget_request.reviewer_feedback = ""
                self.budget_request.save(
                    update_fields=[
                        "status",
                        "reviewer",
                        "reviewer_feedback",
                    ]
                )

                with self.assertRaises(PermissionDenied):
                    review_budget_request(
                        self.manager_user,
                        self.budget_request.pk,
                        "APPROVED",
                    )

                self.budget_request.refresh_from_db()

                self.assertEqual(self.budget_request.status, status)
                self.assertIsNone(self.budget_request.reviewer)
                self.assertEqual(
                    self.budget_request.reviewer_feedback,
                    "",
                )
