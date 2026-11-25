
from django.test import TestCase
from django.contrib.auth.models import User, Group

from apps.budget_requests.models import BudgetRequest

from apps.budget_requests.domain.policies import (
    is_client,
    is_manager,
    is_business_admin,
    can_view_request,
    can_edit_request,
    can_withdraw_request,
    can_review_request,
    is_valid_review,
)


class ClientRoleTest(TestCase):

    def test_client_user_returns_true(self):
        client_group = Group.objects.create(name='Client')
        user = User.objects.create_user(
            username='testclient',
            password='testpassword'
        )
        user.groups.add(client_group)
        self.assertTrue(is_client(user))

    def test_normal_user_returns_false(self):
        user = User.objects.create_user(
            username='normaluser',
            password='testpassword'
        )
        self.assertFalse(is_client(user))

    def test_client_can_view_own_request(self):
        client_group = Group.objects.create(name='Client')
        user = User.objects.create_user(
            username='clientowner',
            password='testpassword'
        )
        user.groups.add(client_group)

        budget_request = BudgetRequest.objects.create(
            title='Office Supplies',
            amount=5000,
            justification='Need office supplies',
            requester=user
        )

        self.assertTrue(can_view_request(user, budget_request))

    def test_client_cannot_view_other_clients_request(self):
        client_group = Group.objects.create(name='Client')

        first_user = User.objects.create_user(
            username='firstclient',
            password='testpassword'
        )
        second_user = User.objects.create_user(
            username='secondclient',
            password='testpassword'
        )

        first_user.groups.add(client_group)
        second_user.groups.add(client_group)

        budget_request = BudgetRequest.objects.create(
            title='Office Equipment',
            amount=10000,
            justification='Need office equipment',
            requester=first_user
        )

        self.assertFalse(
            can_view_request(second_user, budget_request)
        )


class ManagerRoleTest(TestCase):

    def setUp(self):
        self.manager_group = Group.objects.create(name='Manager')
        self.user = User.objects.create_user(
            username='testmanager',
            password='testpassword'
        )
        self.user.groups.add(self.manager_group)

    def test_manager_user_returns_true(self):
        self.assertTrue(is_manager(self.user))

    def test_normal_user_is_not_manager(self):
        user = User.objects.create_user(
            username='normalmanager',
            password='testpassword'
        )
        self.assertFalse(is_manager(user))


class BusinessAdminRoleTest(TestCase):

    def setUp(self):
        self.admin_group = Group.objects.create(name='Admin')
        self.user = User.objects.create_user(
            username='testadmin',
            password='testpassword'
        )
        self.user.groups.add(self.admin_group)

    def test_admin_user_returns_true(self):
        self.assertTrue(is_business_admin(self.user))

    def test_normal_user_is_not_admin(self):
        user = User.objects.create_user(
            username='normaladmin',
            password='testpassword'
        )
        self.assertFalse(is_business_admin(user))


class BudgetRequestPolicyTest(TestCase):

    def setUp(self):
        self.client_group = Group.objects.create(name='Client')
        self.manager_group = Group.objects.create(name='Manager')
        self.admin_group = Group.objects.create(name='Admin')

        self.client_user = User.objects.create_user(
            username='policyclient',
            password='testpassword'
        )
        self.client_user.groups.add(self.client_group)

        self.manager_user = User.objects.create_user(
            username='policymanager',
            password='testpassword'
        )
        self.manager_user.groups.add(self.manager_group)

        self.admin_user = User.objects.create_user(
            username='policyadmin',
            password='testpassword'
        )
        self.admin_user.groups.add(self.admin_group)

        self.other_user = User.objects.create_user(
            username='policyother',
            password='testpassword'
        )
        self.other_user.groups.add(self.client_group)

        self.budget_request = BudgetRequest.objects.create(
            title='Policy Test Request',
            amount=5000,
            justification='Testing budget request policies',
            requester=self.client_user
        )

    def test_owner_can_view_request(self):
        self.assertTrue(
            can_view_request(self.client_user, self.budget_request)
        )

    def test_other_client_cannot_view_request(self):
        self.assertFalse(
            can_view_request(self.other_user, self.budget_request)
        )

    def test_manager_can_view_request(self):
        self.assertTrue(
            can_view_request(self.manager_user, self.budget_request)
        )

    def test_admin_can_view_request(self):
        self.assertTrue(
            can_view_request(self.admin_user, self.budget_request)
        )

    def test_owner_can_edit_request(self):
        self.assertTrue(
            can_edit_request(self.client_user, self.budget_request)
        )

    def test_other_client_cannot_edit_request(self):
        self.assertFalse(
            can_edit_request(self.other_user, self.budget_request)
        )

    def test_owner_can_withdraw_request(self):
        self.assertTrue(
            can_withdraw_request(self.client_user, self.budget_request)
        )

    def test_other_client_cannot_withdraw_request(self):
        self.assertFalse(
            can_withdraw_request(self.other_user, self.budget_request)
        )

    def test_manager_can_review_request(self):
        self.assertTrue(
            can_review_request(self.manager_user, self.budget_request)
        )

    def test_client_cannot_review_request(self):
        self.assertFalse(
            can_review_request(self.client_user, self.budget_request)
        )

    def test_admin_can_review_request(self):
        self.assertTrue(
            can_review_request(self.admin_user, self.budget_request)
        )

    def test_approved_with_empty_feedback_returns_true(self):
        self.assertTrue(is_valid_review('APPROVED', ''))

    def test_rejected_with_feedback_returns_true(self):
        self.assertTrue(
            is_valid_review('REJECTED', 'Budget requirements not met')
        )

    def test_rejected_with_empty_feedback_returns_false(self):
        self.assertFalse(is_valid_review('REJECTED', ''))

    def test_invalid_status_returns_false(self):
        self.assertFalse(
            is_valid_review('INVALID', 'Some feedback')
        )

    def test_client_cannot_edit_approved_request(self):
        self.budget_request.status = 'APPROVED'
        self.budget_request.save()

        self.assertFalse(
            can_edit_request(
                self.client_user,
                self.budget_request
            )
        )

    def test_client_cannot_withdraw_rejected_request(self):
        self.budget_request.status = 'REJECTED'
        self.budget_request.save()

        self.assertFalse(
            can_withdraw_request(
                self.client_user,
                self.budget_request
            )
        )
