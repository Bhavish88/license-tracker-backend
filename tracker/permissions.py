# tracker/permissions.py 
from rest_framework.permissions import BasePermission

class IsOwner(BasePermission):
    """
    Object-level permission:
    - Allow staff/superuser always.
    - Otherwise, allow access ONLY if obj.owner == request.user.
    - No automatic GET allowance for other authenticated users.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        # allow staff or superuser
        if user and (user.is_staff or user.is_superuser):
            return True

        # Try matching standard owner field names
        for attr in ("owner", "user", "created_by"):
            owner = getattr(obj, attr, None)
            if owner is not None:
                return owner == user

        # deny if no owner attribute or mismatch
        return False

