from django.db import models
from core.mixins import TimestampMixin, NamedMixin, SlugMixin, OrderedMixin

class Tag(TimestampMixin, OrderedMixin, NamedMixin, SlugMixin):
    '''Free-form tags for courses.'''

class Topic(TimestampMixin, OrderedMixin, NamedMixin, SlugMixin):
    '''Structured taxonomy for courses (e.g., "Python", "Django", "Databases").'''