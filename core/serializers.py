from rest_framework import serializers
from core.models import Course, Module, Lesson, Enrollment, LessonProgress
from users.serializers import UserSerializer

# ------------------ Lesson ------------------
class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'name', 'slug', 'content', 'duration_seconds', 'order', 'created_at', 'updated_at']
    
    def validate_duration_seconds(self, value):
        if value > 3600 * 4:
            raise serializers.ValidationError("Lesson duration cannot exceed 4 hours.")
        return value


# ------------------ Module ------------------
class ModuleSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'name', 'slug', 'description', 'order', 'lessons', 'created_at', 'updated_at']


# ------------------ Course ------------------
class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    instructors = UserSerializer(many=True, read_only=True)
    total_lessons = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'is_published',
            'tags',
            'topics',
            'instructors',
            'modules',
            'total_lessons',
            'completion_rate',
            'created_at',
            'updated_at',
        ]

    def get_total_lessons(self, obj):
        return obj.total_lessons()

    def get_completion_rate(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            return obj.completion_for(user)
        return None
    

class CourseMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'name', 'slug']


class CourseDynamicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'name', 'slug', 'description', 'modules']

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)
        super().__init__(*args, **kwargs)
        if fields:
            allowed = set(fields)
            existing = set(self.fields)
            for field in existing - allowed:
                self.fields.pop(field)


# ------------------ Enrollment ------------------
class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'user', 'enrolled_at', 'progress_percent']

    def get_progress_percent(self, obj):
        return obj.progress_percent()


# ------------------ LessonProgress ------------------
class LessonProgressSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    lesson = LessonSerializer(read_only=True)

    class Meta:
        model = LessonProgress
        fields = ['id', 'user', 'lesson', 'completed', 'completed_at', 'created_at', 'updated_at']
