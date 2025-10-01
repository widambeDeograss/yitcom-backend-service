from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from apps.accounts.models import Notification, User
from .models import Discussion, Comment, Reaction, Forum
from ..newsletters.signals import send_email_via_smtp


@receiver(post_save, sender=Discussion)
def notify_followers_new_discussion(sender, instance, created, **kwargs):
    """
    Notify all followers of a forum when a new discussion is created
    and send email to forum author
    """
    if created:
        forum = instance.forum
        followers = forum.followers.exclude(id=instance.author.id)

        # Create notifications for followers
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

        # Send email to forum author (if different from discussion author)
        if forum.created_by != instance.author:
            send_discussion_notification_email(forum.created_by, instance, forum)


def send_discussion_notification_email(forum_author, discussion, forum):
    """Send email notification to forum author about new discussion"""
    subject = f"New Discussion in Your Forum: {forum.title}"

    # HTML email template
    html_content = f"""
    <html>
      <head></head>
      <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
          <h2 style="color: #4a6baf;">New Discussion in Your Forum</h2>
          <h3>{forum.title}</h3>
          <p><strong>New discussion started by:</strong> {discussion.author.username}</p>
          <p><strong>Discussion title:</strong> {discussion.title}</p>
          <p><strong>Content:</strong> {discussion.content[:200]}...</p>
          <div style="text-align: center; margin: 30px 0;">
            <a href="{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/forums/{forum.id}" 
               style="background: #4a6baf; color: white; padding: 12px 24px; 
                      text-decoration: none; border-radius: 4px; display: inline-block;">
              View Forum
            </a>
          </div>
          <p style="margin-top: 30px; font-size: 0.9em; color: #666;">
            You received this email because you created this forum.
          </p>
        </div>
      </body>
    </html>
    """

    # Plain text version
    text_content = f"""
    New Discussion in Your Forum: {forum.title}

    New discussion started by: {discussion.author.username}
    Discussion title: {discussion.title}
    Content: {discussion.content[:200]}...

    View the forum here: {getattr(settings, 'SITE_URL', 'http://localhost:8000')}/forums/{forum.id}

    You received this email because you created this forum.
    """

    print(f"====================SENDING DISCUSSION NOTIFICATION TO: {forum_author.email}")
    send_email_via_smtp(
        recipient=forum_author.email,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )

@receiver(post_save, sender=Reaction)
def notify_reaction_to_followers(sender, instance, created, **kwargs):
    """
    Notify forum followers when someone reacts to a discussion
    """
    if created:
        content_object = instance.content_object

        # Only handle reactions to discussions for now
        if isinstance(content_object, Discussion):
            discussion = content_object
            forum = discussion.forum

            # Get followers excluding the user who reacted
            followers = forum.followers.exclude(id=instance.user.id)

            notifications = [
                Notification(
                    user=follower,
                    notification_type='new_reaction',
                    title=f"New reaction on discussion in {forum.title}",
                    message=f"{instance.user.username} reacted with {instance.reaction} to {discussion.title}",
                    content_type=ContentType.objects.get_for_model(instance),
                    object_id=instance.id
                )
                for follower in followers
            ]

            if notifications:
                Notification.objects.bulk_create(notifications)

            # Also notify the discussion author if it's not the reactor
            if discussion.author != instance.user:
                Notification.objects.create(
                    user=discussion.author,
                    notification_type='new_reaction',
                    title=f"New reaction on your discussion",
                    message=f"{instance.user.username} reacted with {instance.reaction} to your discussion",
                    content_type=ContentType.objects.get_for_model(instance),
                    object_id=instance.id
                )



def notify_discussion_participants_and_followers(sender, instance, created, **kwargs):
    """
    Notify discussion participants AND forum followers when a new comment is added
    """
    if created:
        discussion = instance.discussion
        forum = discussion.forum

        # Get forum followers excluding the comment author
        forum_followers = forum.followers.exclude(id=instance.author.id)

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

        # Combine forum followers and other commenters, removing duplicates
        all_recipients = set(forum_followers) | set(other_commenters)

        notifications = [
            Notification(
                user=recipient,
                notification_type='new_comment',
                title=f"New comment on {discussion.title}",
                message=f"{instance.author.username} commented on {discussion.title} in {forum.title}",
                content_type=ContentType.objects.get_for_model(instance),
                object_id=instance.id
            )
            for recipient in all_recipients
        ]

        if notifications:
            Notification.objects.bulk_create(notifications)