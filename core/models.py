from django.conf import settings
from django.db import models
from core.mixins import TimestampMixin, NamedMixin, SlugMixin, OrderedMixin

class Course(TimestampMixin, OrderedMixin, NamedMixin, SlugMixin):
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)

    tags = models.ManyToManyField("lookups.Tag", blank=True, related_name="courses")
    topics = models.ManyToManyField("lookups.Topic", blank=True, related_name="courses")
    instructors = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="courses_taught"
    )
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="Enrollment",
        related_name="enrolled_courses",
        blank=True,
    )

    def total_lessons(self):
        return Lesson.objects.filter(module__course=self).count()

    def completion_for(self, user):
        total = self.total_lessons()
        if total == 0:
            return 0.0
        completed = LessonProgress.objects.filter(
            user=user, lesson__module__course=self, completed=True
        ).count()
        return round((completed / total) * 100, 2)

class Module(TimestampMixin, OrderedMixin, NamedMixin, SlugMixin):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    description = models.TextField(blank=True)

    class Meta(OrderedMixin.Meta):
        unique_together = (("course", "slug"),)

class Lesson(TimestampMixin, OrderedMixin, NamedMixin, SlugMixin):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    content = models.TextField(blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta(OrderedMixin.Meta):
        unique_together = (("module", "slug"),)

class Enrollment(TimestampMixin):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("course", "user"),)

    def __str__(self):
        return f"{self.user} in {self.course}"

    def progress_percent(self):
        return self.course.completion_for(self.user)

class LessonProgress(TimestampMixin):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress_records")
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = (("user", "lesson"),)