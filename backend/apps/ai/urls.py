from django.urls import path

from .api import ProposalConfirmView, ProposalDetailView, ProposalGenerateView
from .feedback_api import FeedbackAnalyzeView


app_name = "ai"

_prefix = "profiles/<str:profile_id>/workspaces/<str:workspace_id>/ai/task-proposals/"

urlpatterns = [
    path("profiles/<str:profile_id>/workspaces/<str:workspace_id>/tasks/<str:task_id>/ai/feedback-analysis/",
         FeedbackAnalyzeView.as_view(), name="feedback-analyze"),
    path(_prefix, ProposalGenerateView.as_view(), name="proposal-generate"),
    path(f"{_prefix}<str:proposal_id>/", ProposalDetailView.as_view(), name="proposal-detail"),
    path(f"{_prefix}<str:proposal_id>/confirm/", ProposalConfirmView.as_view(), name="proposal-confirm"),
]
