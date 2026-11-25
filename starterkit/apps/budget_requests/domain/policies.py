def is_client(user):
    return (
        user.is_authenticated
        and user.groups.filter(name='Client').exists()
    )


def is_manager(user):
    return (
        user.is_authenticated
        and user.groups.filter(name='Manager').exists()
    )


def is_business_admin(user):
    return (
        user.is_authenticated
        and user.groups.filter(name='Admin').exists()
    )


def can_view_request(user, budget_request):
    if not user.is_authenticated:
        return False

    if is_manager(user) or is_business_admin(user):
        return True

    if is_client(user):
        return budget_request.requester == user

    return False


def can_edit_request(user, budget_request):
    return (
        is_client(user)
        and budget_request.requester == user
        and budget_request.status == 'PENDING'
    )


def can_withdraw_request(user, budget_request):
    return (
        is_client(user)
        and budget_request.requester == user
        and budget_request.status == 'PENDING'
    )


def can_review_request(user, budget_request):
    return (
        user.is_authenticated
        and (is_manager(user) or is_business_admin(user))
        and budget_request.status == 'PENDING'
    )


def is_valid_review(status, feedback):
    if status not in ['APPROVED', 'REJECTED']:
        return False

    if status == 'REJECTED' and not feedback.strip():
        return False

    return True