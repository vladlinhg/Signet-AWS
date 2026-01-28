from django.db import models

class SupportingDocument(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='supporting_documents/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
