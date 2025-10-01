import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from concurrent.futures import ThreadPoolExecutor
from django.dispatch import Signal, receiver
import requests
import json
from django.conf import settings
import logging

from apps.blogs.models import Blog
from apps.newsletters.models import NewsletterSubscription

logger = logging.getLogger(__name__)

# Define signals
send_sms_and_email_for_verification_signal = Signal()
send_sms_and_email_due_to_status_signal = Signal()

# Email configuration - should come from Django settings
EMAIL_HOST = getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = getattr(settings, 'EMAIL_PORT', 587)
EMAIL_HOST_USER = getattr(settings, 'EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = getattr(settings, 'EMAIL_USE_TLS', True)
DEFAULT_FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# SMS configuration
SMS_API_URL = getattr(settings, 'SMS_API_URL', '')
SMS_API_KEY = getattr(settings, 'SMS_API_KEY', '')


def send_email_via_smtp(recipient, subject, html_content, text_content=None):
    """
    Send email using Gmail SMTP with HTML support
    """
    if not text_content:
        text_content = "Please enable HTML to view this message"

    try:
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = DEFAULT_FROM_EMAIL
        msg['To'] = recipient

        # Record the MIME types of both parts - text/plain and text/html
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')

        # Attach parts into message container
        msg.attach(part1)
        msg.attach(part2)

        # Send the message via SMTP server
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.ehlo()
            if EMAIL_USE_TLS:
                server.starttls()
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.sendmail(DEFAULT_FROM_EMAIL, recipient, msg.as_string())

        logger.info(f"Email sent successfully to {recipient}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {str(e)}")
        return False


def send_verification_notification(phone_number=None, email=None, message='Hey'):
    """
    Send verification notification (can be SMS and/or email)
    """

    # HTML template for verification email
    html_email = f"""
    <html>
      <head></head>
      <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
          <h2 style="color: #4a6baf;">YIT SUBSCRIPTION NOTICE</h2>
          <p>{message}</p>
          <p style="margin-top: 30px; font-size: 0.9em; color: #666;">
            If you didn't request this, please ignore this message.
          </p>
        </div>
      </body>
    </html>
    """

    # if phone_number:
    #     send_sms_via_api(phone_number, message)

    if email:
        print(" ====================REACHED")
        send_email_via_smtp(
            recipient=email,
            subject="YIT SUBSCRIPTION NOTICE",
            html_content=html_email,
            text_content=message
        )


# Add this to your existing email file or models.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

# Define a new signal for blog newsletter
blog_newsletter_signal = Signal()


@receiver(post_save, sender=Blog)
def send_blog_newsletter_on_create(sender, instance, created, **kwargs):
    """
    Send newsletter email to subscribers when a new blog is created and published
    """
    if created and instance.is_published:
        blog_newsletter_signal.send(sender=sender, blog=instance)


@receiver(blog_newsletter_signal)
def handle_blog_newsletter(sender, **kwargs):
    """
    Handle blog newsletter email sending to all subscribers
    """
    blog = kwargs['blog']

    # Get all active newsletter subscribers
    subscribers = NewsletterSubscription.objects.filter(is_active=True)
    # Build the blog URL (adjust based on your website)
    blog_url = f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/blogs/{blog.slug}"  # Change to your actual URL

    # Send email to each subscriber
    for subscriber in subscribers:
        send_blog_newsletter_email(subscriber.email, blog, blog_url)


def send_blog_newsletter_email(subscriber_email, blog, blog_url):
    print(blog)
    """
    Send individual blog newsletter email to a subscriber
    """
    subject = f"New Blog Post: {blog.title}"

    # HTML email template for the blog newsletter
    html_content = f"""
<html>
  <head></head>
  <body style="font-family: Arial, sans-serif; line-height: 1.6;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
      <h2 style="color: #4a6baf;">New Blog Post Published!</h2>
      <h3>{blog.title}</h3>
      
      <div style="text-align: center; margin: 20px 0;">
        <img src="{{ blog.featured_image }}" 
             alt="{{ blog.title }}"
             style="max-width: 100%; height: auto; border-radius: 8px; max-height: 300px; object-fit: cover;">
      </div>
      
      <p>{{ blog.content|striptags|truncatewords:50 }}...</p>
      
      <div style="text-align: center; margin: 30px 0;">
        <a href="{blog_url}" 
           style="background: #4a6baf; color: white; padding: 12px 24px; 
                  text-decoration: none; border-radius: 4px; display: inline-block;">
          Read Full Blog Post
        </a>
      </div>
      
      <p style="margin-top: 30px; font-size: 0.9em; color: #666;">
        You received this email because you subscribed to our newsletter.<br>
        <a href="https://yourwebsite.com/unsubscribe">Unsubscribe</a>
      </p>
    </div>
  </body>
</html>
    """

    # Plain text version
    text_content = f"""
    New Blog Post: {blog.title}

    {blog.content[:200]}...

    Read the full post here: {blog_url}

    Visit our website: https://yourwebsite.com

    You received this email because you subscribed to our newsletter.
    To unsubscribe, visit: https://yourwebsite.com/unsubscribe
    """

    # Use your existing email function
    print(f"====================SENDING BLOG NEWSLETTER TO: {subscriber_email}")
    send_email_via_smtp(
        recipient=subscriber_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
