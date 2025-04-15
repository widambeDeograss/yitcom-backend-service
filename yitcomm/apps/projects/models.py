from django.db import models

from apps.accounts.models import Skill, TechCategory, User

# Create your models here.
class Project(models.Model):
    """Tech projects showcased by community members."""
    title = models.CharField(max_length=200)
    description = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    contributors = models.ManyToManyField(User, related_name='contributed_projects', blank=True)
    github_url = models.URLField(blank=True)
    project_url = models.URLField(blank=True)
    categories = models.ManyToManyField(TechCategory, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    featured_image = models.ImageField(upload_to='project_images/', blank=True, null=True)
    technologies_used = models.ManyToManyField(Skill, related_name='projects_used_in')
    deleted =  models.BooleanField(default=False)
    drafted = models.BooleanField(default=False)
    published = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'

        indexes = [
            models.Index(fields=['title']),
        ]
        

