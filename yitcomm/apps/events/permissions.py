from rest_framework import permissions

class IsOrganizerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow organizers of an event or admins to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the organizer or admin.
        return request.user == obj.organizer or request.user.is_staff