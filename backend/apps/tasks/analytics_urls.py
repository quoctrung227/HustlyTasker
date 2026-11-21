from django.urls import path

from .analytics_views import AnalyticsEmployeeDetailView, AnalyticsEmployeeListView, AnalyticsSummaryView


urlpatterns = [
    path("profiles/<str:profile_id>/analytics/", AnalyticsSummaryView.as_view(), name="task-analytics"),
    path("profiles/<str:profile_id>/analytics/employees/", AnalyticsEmployeeListView.as_view(), name="task-analytics-employees"),
    path("profiles/<str:profile_id>/analytics/employees/<str:membership_id>/", AnalyticsEmployeeDetailView.as_view(), name="task-analytics-employee-detail"),
]
