# django-full-course-2025-part-4

**Production‑Ready Django REST Framework Views (Courses App)**  
Part 4 of the Django Full Course (2025 Edition)

- **Created at:** 2025‑11‑06
- **Created by:** `Arun Godwin Patel @ Code Creations`

This part connects the serializers from Part 3 to **Django REST Framework (DRF) views**. We’ll build **clean, secure, and scalable** endpoints for courses, modules, lessons, enrollments, and lesson progress — with **permissions, filtering, pagination, throttling, and performance** baked in.

---

## 🔭 Overview

In this part, you’ll learn how to:

- Pick the right view type: **APIView vs generics vs ViewSets**
- Wire up **routers** and **nested routes**
- Add **permissions** (built‑in + custom)
- Implement **filtering / search / ordering / pagination**
- Add **throttling** & **rate limits**
- Optimise **query performance** with `select_related` / `prefetch_related`
- Build **custom actions** for non‑CRUD operations
- Handle **errors** and return consistent API responses
- **Testing** the views
- Ship **OpenAPI** docs automatically

> We’ll use the same data model from earlier parts: `Course`, `Module`, `Lesson`, `Enrollment`, `LessonProgress`, and `UserProfile`.

---

## ⚙️ Setup (requirements & settings)

Install / update DRF + helpers:

```bash
pip install djangorestframework drf-nested-routers django-filter
```

Enable apps and DRF defaults in `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    "rest_framework",
    "django_filters",
    "core",
    "users",
]

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/min",
    },
}
```

> All API endpoints are **publicly accessible** in this version.

---

## 🧱 Picking the right view type

**APIView**

- Maximum control. You implement HTTP verbs yourself.
- Great for webhooks, unusual request parsing, and streaming.

**Generic Views** (`ListCreateAPIView`, `RetrieveUpdateDestroyAPIView`)

- Common CRUD with minimal code. Override `get_queryset`, `perform_create`, etc.

**ViewSets** (`ModelViewSet`)

- Best for RESTful resources + routers generate routes for you.
- Add **custom actions** (`@action`) when you need non‑CRUD verbs.

> **We’ll use ViewSets** for most endpoints and sprinkle in generics where helpful.

---

## 📁 Project structure (relevant parts)

```
project/
  core/
    models.py
    views.py
    serializers.py
    permissions.py
    urls.py
  users/
    serializers.py
project/
  urls.py
```

---

## 🔐 Permissions

Although this build allows public access, it’s still good practice to include basic permission scaffolding for future private endpoints.

```python
from rest_framework.permissions import BasePermission, SAFE_METHODS

class ReadOnly(BasePermission):
    """Allow all safe (GET, HEAD, OPTIONS) requests."""
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
```

Use `ReadOnly` for public endpoints, and later replace it with user‑level or role‑based checks when needed.

---

## 🚦 Views with ViewSets

```python
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response

from django.db.models import Prefetch

from core.models import Course, Module, Lesson, Enrollment, LessonProgress
from core.serializers import (
    CourseSerializer, ModuleSerializer, LessonSerializer,
    EnrollmentSerializer, LessonProgressSerializer,
)
```

### CourseViewSet

```python
class CourseViewSet(viewsets.ModelViewSet):
    queryset = (
        Course.objects.select_related()
        .prefetch_related(
            "topics",
            "tags",
            "instructors",
            Prefetch("modules__lessons", queryset=Lesson.objects.only("id", "name", "slug", "order"))
        )
    )
    serializer_class = CourseSerializer

    filterset_fields = ["is_published", "tags", "topics"]
    search_fields = ["name", "slug", "description"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["-created_at"]

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Custom action: publish a course."""
        course = self.get_object()
        course.is_published = True
        course.save(update_fields=["is_published"])
        return Response({"status": "published"})
```

### ModuleViewSet

```python
class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.select_related("course").prefetch_related("lessons")
    serializer_class = ModuleSerializer

    filterset_fields = ["course"]
    search_fields = ["name", "slug", "description"]
    ordering_fields = ["order", "created_at", "updated_at"]
    ordering = ["order"]

    def get_queryset(self):
        qs = super().get_queryset()
        # If this is a nested route: /api/courses/<course_pk>/modules/
        course_pk = self.kwargs.get("course_pk")
        if course_pk:
            qs = qs.filter(course_id=course_pk)
        return qs

    def perform_create(self, serializer):
        # If nested, bind the FK from the URL; otherwise allow explicit course in body (optional)
        course_pk = self.kwargs.get("course_pk")
        if course_pk:
            course = get_object_or_404(Course, pk=course_pk)
            serializer.save(course=course)
        else:
            # Non-nested POST to /api/modules/ can still work if course provided
            serializer.save()
```

### LessonViewSet

```python
class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.select_related("module", "module__course")
    serializer_class = LessonSerializer

    filterset_fields = ["module", "module__course"]
    search_fields = ["name", "slug", "content"]
    ordering_fields = ["order", "created_at", "updated_at"]
    ordering = ["order"]

    def get_queryset(self):
        qs = super().get_queryset()
        module_pk = self.kwargs.get("module_pk")
        if module_pk:
            qs = qs.filter(module_id=module_pk)
        return qs

    def perform_create(self, serializer):
        module_pk = self.kwargs.get("module_pk")
        if module_pk:
            module = get_object_or_404(Module, pk=module_pk)
            serializer.save(module=module)
        else:
            serializer.save()

    @action(detail=True, methods=["post"], url_path="mark-complete")  # optional, for hyphen URL
    def mark_complete(self, request, *args, **kwargs):
        """
        Custom action: mark a lesson as complete.
        Accept *args, **kwargs so nested router's module_pk doesn't break the signature.
        """
        lesson = self.get_object()  # respects get_queryset() filtering w/ module_pk
        # ⚠️ If LessonProgress.user is NOT nullable, don't pass user=None — it will 500.
        # For a public API, either make user nullable or gate this behind auth.
        LessonProgress.objects.update_or_create(
            user=None,  # only works if FK allows nulls; otherwise replace with request.user
            lesson=lesson,
            defaults={"completed": True},
        )
        return Response({"status": "completed"})
```

### LessonProgressViewSet

```python
class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.select_related("module", "module__course")
    serializer_class = LessonSerializer

    filterset_fields = ["module", "module__course"]
    search_fields = ["name", "slug", "content"]
    ordering_fields = ["order", "created_at", "updated_at"]
    ordering = ["order"]

    def get_queryset(self):
        qs = super().get_queryset()
        module_pk = self.kwargs.get("module_pk")
        if module_pk:
            qs = qs.filter(module_id=module_pk)
        return qs

    def perform_create(self, serializer):
        module_pk = self.kwargs.get("module_pk")
        if module_pk:
            module = get_object_or_404(Module, pk=module_pk)
            serializer.save(module=module)
        else:
            serializer.save()

    @action(detail=True, methods=["post"], url_path="mark-complete")  # optional, for hyphen URL
    def mark_complete(self, request, *args, **kwargs):
        """
        Custom action: mark a lesson as complete.
        Accept *args, **kwargs so nested router's module_pk doesn't break the signature.
        """
        lesson = self.get_object()  # respects get_queryset() filtering w/ module_pk
        # ⚠️ If LessonProgress.user is NOT nullable, don't pass user=None — it will 500.
        # For a public API, either make user nullable or gate this behind auth.
        LessonProgress.objects.update_or_create(
            user=None,  # only works if FK allows nulls; otherwise replace with request.user
            lesson=lesson,
            defaults={"completed": True},
        )
        return Response({"status": "completed"})
```

---

## 🧭 Routers & Nested Routes

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from core.views import CourseViewSet, ModuleViewSet, LessonViewSet

router = DefaultRouter()
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"modules", ModuleViewSet, basename="module")
router.register(r"lessons", LessonViewSet, basename="lesson")

courses_router = NestedDefaultRouter(router, r"courses", lookup="course")
courses_router.register(r"modules", ModuleViewSet, basename="course-modules")

modules_router = NestedDefaultRouter(router, r"modules", lookup="module")
modules_router.register(r"lessons", LessonViewSet, basename="module-lessons")

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/", include(courses_router.urls)),
    path("api/", include(modules_router.urls)),
]
```

---

## 🔎 Filtering, Search, Ordering, Pagination

Examples:

```
GET /api/courses/?is_published=true&ordering=-created_at
GET /api/courses/?search=django
GET /api/lessons/?module=<uuid>&ordering=order
GET /api/courses/?page=2
```

---

## 🚀 Performance (query optimisation & caching)

- Use `select_related` for single‑valued relationships.
- Use `prefetch_related` for M2M and reverse relationships.
- Keep serializers light for list endpoints.
- Consider caching popular endpoints.
- Test with the **Django Debug Toolbar** to measure query count.

---

## 🧩 Custom Actions (beyond CRUD)

- **CRUD** endpoints (Create, Read, Update, Delete) come built into `ModelViewSet`.
- Use `@action` when you need **custom API operations** that don’t fit CRUD.

Example 1: single‑object action (`detail=True`)

```python
class CourseViewSet(viewsets.ModelViewSet):
    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        course = self.get_object()
        course.is_published = True
        course.save(update_fields=["is_published"])
        return Response({"status": "published"})
```

→ `POST /api/courses/<id>/publish/` will publish that course.

Example 2: collection‑level action (`detail=False`)

```python
class CourseViewSet(viewsets.ModelViewSet):
    @action(detail=False, methods=["get"])
    def featured(self, request):
        featured = Course.objects.filter(is_published=True)[:5]
        serializer = self.get_serializer(featured, many=True)
        return Response(serializer.data)
```

→ `GET /api/courses/featured/` returns the latest 5 published courses.

**Why use them?**  
They let you create **semantic endpoints** like `/api/courses/<id>/publish/`, `/api/lessons/<id>/mark_complete/`, or `/api/courses/featured/` that encapsulate **domain‑specific actions** without polluting CRUD logic.

---

## Testing the Views

- `/api/courses/`: List or create all courses
- `/api/courses/1/`: Retrieve or update a specific course
- `/api/courses/1/modules/`: List all modules belonging to course 1
- `/api/courses/1/modules/3/`: Get details of module 3 within course 1
- `/api/modules/3/lessons/`: List all lessons in module 3
- `/api/modules/3/lessons/7/`: Retrieve lesson 7 from module 3

---

## 📜 OpenAPI / Schema & Docs

```bash
pip install drf-spectacular
```

```python
INSTALLED_APPS += ["drf_spectacular"]
REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = "drf_spectacular.openapi.AutoSchema"
SPECTACULAR_SETTINGS = {"TITLE": "Courses API", "VERSION": "1.0.0"}
```

```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
```

---

**Created by:** `Arun Godwin Patel`  
**Brand:** `Code Creations`  
**Year:** 2025
