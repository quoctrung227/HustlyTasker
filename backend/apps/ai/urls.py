from django.urls import path

from .api import ProposalConfirmView, ProposalDetailView, ProposalGenerateView


app_name = "ai"

_prefix = "profiles/<str:profile_id>/workspaces/<str:workspace_id>/ai/task-proposals/"

urlpatterns = [
    path(_prefix, ProposalGenerateView.as_view(), name="proposal-generate"),
    path(f"{_prefix}<str:proposal_id>/", ProposalDetailView.as_view(), name="proposal-detail"),
    path(f"{_prefix}<str:proposal_id>/confirm/", ProposalConfirmView.as_view(), name="proposal-confirm"),
]
