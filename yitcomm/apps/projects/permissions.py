from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Allow read-only for published projects
        if request.method in permissions.SAFE_METHODS:
            return obj.published or obj.author == request.user
            
        # Only allow modifications by owner
        return obj.author == request.user