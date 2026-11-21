from django.urls import path

from .views import TrashActionView, TrashListView

app_name = "trash"
urlpatterns = [path("trash/", TrashListView.as_view(), name="list")]
for kind in ("task", "workspace", "profile"):
    for action in ("delete", "restore", "purge"):
        urlpatterns.append(path(f"trash/{kind}/<uuid:object_id>/{action}/", TrashActionView.as_view(),
                                {"object_type": kind, "action": action}, name=f"{kind}-{action}"))
