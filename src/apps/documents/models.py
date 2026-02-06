from django.db import models

class SupportingDocument(models.Model):
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='supporting_documents/')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.title:
            import uuid
            # Auto-generate unique name
            self.title = f"DOC-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        filename = self.file.name.split('/')[-1] if self.file else ""
        return f"{self.title} ({filename})"
