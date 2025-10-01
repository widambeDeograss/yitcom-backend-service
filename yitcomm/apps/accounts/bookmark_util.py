from django.contrib.contenttypes.models import ContentType
from .models import Bookmark

def get_bookmark_status(user, obj):
    """Check if an object is bookmarked by a user and return bookmark data if exists."""
    if not user.is_authenticated:
        return {'is_bookmarked': False, 'bookmark': None}
    
    content_type = ContentType.objects.get_for_model(obj)
    try:
        bookmark = Bookmark.objects.get(
            user=user,
            content_type=content_type,
            object_id=obj.id
        )
        return {
            'is_bookmarked': True,
            'bookmark': {
                'id': bookmark.id,
                'notes': bookmark.notes,
                'folder': bookmark.folder,
                'created_at': bookmark.created_at
            }
        }
    except Bookmark.DoesNotExist:
        return {'is_bookmarked': False, 'bookmark': None}