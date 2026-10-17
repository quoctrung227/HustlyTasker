from django.urls import include, path

from .views import HealthCheckView


urlpatterns = [
    path(
        "auth/",
        include("apps.accounts.urls"),
    ),

    path(
        "health/",
        HealthCheckView.as_view(),
        name="health",
    ),
]
