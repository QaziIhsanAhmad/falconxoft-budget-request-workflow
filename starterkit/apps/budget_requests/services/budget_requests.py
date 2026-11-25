
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.budget_requests.models import BudgetRequest
from apps.budget_requests.domain.policies import (
    is_client,
    can_edit_request,
)


@transaction.atomic
def create_budget_request(user, validated_data):
    # Only authenticated Clients can create requests
    if not is_client(user):
        raise PermissionDenied(
            "Only authenticated Clients can create budget requests."
        )

    allowed_fields = {
        "title",
        "amount",
        "justification",
    }

    if not isinstance(validated_data, dict):
        raise ValidationError("Invalid request data.")

    if set(validated_data.keys()) != allowed_fields:
        raise ValidationError(
            "Title, amount and justification are required. "
            "Additional fields are not allowed."
        )

    # Requester and status are controlled by the server
    budget_request = BudgetRequest(
        title=validated_data["title"],
        amount=validated_data["amount"],
        justification=validated_data["justification"],
        requester=user,
        status="PENDING",
    )

    budget_request.full_clean()
    budget_request.save()

    return budget_request


@transaction.atomic
def update_budget_request(user, budget_request, validated_data):
    # Only the owning Client can edit their pending request
    if not can_edit_request(user, budget_request):
        raise PermissionDenied(
            "You cannot edit this budget request."
        )

    allowed_fields = {
        "title",
        "amount",
        "justification",
    }

    if not isinstance(validated_data, dict):
        raise ValidationError("Invalid update data.")

    if not validated_data:
        raise ValidationError("At least one field is required.")

    if not set(validated_data.keys()).issubset(allowed_fields):
        raise ValidationError(
            "Only title, amount and justification can be updated."
        )

    # Update only permitted fields
    for field, value in validated_data.items():
        setattr(budget_request, field, value)

    # Validate all model fields before saving
    budget_request.full_clean()

    # Save only updated fields
    budget_request.save(
        update_fields=[
            *validated_data.keys(),
            "updated_at",
        ]
    )

    return budget_request
