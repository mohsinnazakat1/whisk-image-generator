from django.db import models

class WhiskSettings(models.Model):
    auth_token = models.CharField(max_length=500, help_text="Authentication token for Whisk API")
    project_id = models.CharField(max_length=100, help_text="Default project ID for Whisk API")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Whisk Settings"
        verbose_name_plural = "Whisk Settings"

    def __str__(self):
        return f"Whisk Settings (Last updated: {self.updated_at})"

    @classmethod
    def get_settings(cls):
        settings = cls.objects.first()
        if not settings:
            settings = cls.objects.create(
                auth_token="",
                project_id=""
            )
        return settings

class BulkImageRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ImagePrompt(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    bulk_request = models.ForeignKey(BulkImageRequest, related_name='prompts', on_delete=models.CASCADE)
    prompt_text = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    generated_image = models.TextField(blank=True, null=True)  # Stores base64 image data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)