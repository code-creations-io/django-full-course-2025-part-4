from django.db import models
from django.utils.text import slugify
from django.utils import timezone

class TimestampMixin(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class OrderedMixin(models.Model):
    order = models.PositiveIntegerField(default=0, help_text="Lower comes first.")

    class Meta:
        abstract = True
        ordering = ('order',)

class NamedMixin(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return getattr(self, "name", super().__str__())

    class Meta:
        abstract = True

class SlugMixin(models.Model):
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    slug_source_field = "name"

    def save(self, *args, **kwargs):
        if not self.slug:
            source = getattr(self, self.slug_source_field, None)
            if source:
                base = slugify(source)[:200]
                candidate = base
                i = 2
                Model = self.__class__
                while Model.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                    candidate = f"{base}-{i}"
                    i += 1
                self.slug = candidate
        super().save(*args, **kwargs)

    class Meta:
        abstract = True