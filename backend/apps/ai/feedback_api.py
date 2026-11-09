"""Authenticated advisory feedback fixture transport; no persistence or actions."""

from collections.abc import Mapping

from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .api import (
    FixtureGenerationDayThrottle,
    FixtureGenerationMinuteThrottle,
    ProposalApiMixin,
    SafeAIInputSerializer,
)
from .feedback_services import analyze_feedback


class FeedbackAnalyzeSerializer(SafeAIInputSerializer):
    sources = serializers.JSONField()
    focus = serializers.CharField(required=False, allow_blank=True, max_length=1000,
                                  trim_whitespace=False)

    @sensitive_variables()
    def to_internal_value(self, data):
        if isinstance(data, Mapping) and "focus" in data and type(data["focus"]) is not str:
            raise serializers.ValidationError({"focus": ["A text focus is required."]})
        return super().to_internal_value(data)


@method_decorator(never_cache, name="dispatch")
@method_decorator(sensitive_post_parameters(), name="dispatch")
class FeedbackAnalyzeView(ProposalApiMixin, APIView):
    http_method_names = ("post", "options")
    # Reuse both the rates AND cache scope: analysis cannot multiply the existing
    # per-user fixture quota by switching between Generator and Analyzer routes.
    throttle_classes = (FixtureGenerationMinuteThrottle, FixtureGenerationDayThrottle)

    def get_throttles(self):
        if self.request.method == "OPTIONS":
            return []
        return super().get_throttles()

    @sensitive_variables()
    def post(self, request, **kwargs):
        serializer = FeedbackAnalyzeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = analyze_feedback(
            **self.scope_kwargs(), task_id=kwargs["task_id"],
            **serializer.validated_data,
        )
        return Response(result, status=status.HTTP_200_OK)
