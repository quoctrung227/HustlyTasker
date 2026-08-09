from django.urls import path
from django.http import JsonResponse


def api_test(request):

    return JsonResponse(
        {
            "message": "HustlyTasker API is working"
        }
    )


urlpatterns = [

    path(
        "test/",
        api_test
    ),

]