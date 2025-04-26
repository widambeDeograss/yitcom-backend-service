from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from  apps.accounts.models import Notification, User
from .models import Discussion, Comment, Reaction

@receiver(post_save, sender=Discussion)
def notify_followers_new_discussion(sender, instance, created, **kwargs):
    if created:
        forum = instance.forum
        followers = forum.followers.exclude(id=instance.author.id)
        
        notifications = [
            Notification(
                user=follower,
                notification_type='new_discussion',
                title=f"New discussion in {forum.title}",
                message=f"{instance.author.username} started a new discussion: {instance.title}",
                content_type=ContentType.objects.get_for_model(instance),
                object_id=instance.id
            )
            for follower in followers
        ]
        Notification.objects.bulk_create(notifications)

@receiver(post_save, sender=Comment)
def notify_discussion_participants(sender, instance, created, **kwargs):
    if created:
        discussion = instance.discussion
        
        # Notify discussion author if it's not the comment author
        if discussion.author != instance.author:
            Notification.objects.create(
                user=discussion.author,
                notification_type='new_comment',
                title=f"New comment on your discussion",
                message=f"{instance.author.username} commented on your discussion: {discussion.title}",
                content_type=ContentType.objects.get_for_model(instance),
                object_id=instance.id
            )
        
        # Notify other commenters (excluding discussion author and comment author)
        other_commenters = User.objects.filter(
            forum_comments__discussion=discussion
        ).exclude(
            id__in=[discussion.author.id, instance.author.id]
        ).distinct()
        
        notifications = [
            Notification(
                user=commenter,
                notification_type='new_comment',
                title=f"New comment on {discussion.title}",
                message=f"{instance.author.username} also commented on {discussion.title}",
                content_type=ContentType.objects.get_for_model(instance),
                object_id=instance.id
            )
            for commenter in other_commenters
        ]
        Notification.objects.bulk_create(notifications)

@receiver(post_save, sender=Reaction)
def notify_reaction(sender, instance, created, **kwargs):
    if created:
        content_object = instance.content_object
        if instance.user != content_object.author:
            Notification.objects.create(
                user=content_object.author,
                notification_type='new_reaction',
                title=f"New reaction on your {content_object._meta.model_name}",
                message=f"{instance.user.username} reacted with {instance.reaction} to your {content_object._meta.model_name}",
                content_type=ContentType.objects.get_for_model(instance),
                object_id=instance.id
            )