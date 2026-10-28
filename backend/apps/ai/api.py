"""Authenticated, tenant-scoped fixture proposal transport; no live provider."""

import json
from collections.abc import Mapping
from uuid import UUID

from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from rest_framework import serializers, status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.tasks.permissions import CanManageWorkspaceTasks
from apps.workspace.serializers import StrictInputSerializer
from apps.workspace.views import TenantApiViewMixin

from . import durable_services
from .errors import AIError


MAX_REQUEST_BYTES = 32 * 1024


class BoundedStrictJSONParser(JSONParser):
    """Bound before parsing; never include input or unknown keys in failures."""

    @sensitive_variables("raw", "data")
    def parse(self, stream, media_type=None, parser_context=None):
        raw = stream.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise ParseError("Request body exceeds the allowed size.")

        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError()
                result[key] = value
            return result

        def reject_constant(value):
            raise ValueError()

        try:
            data = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=unique_object,
                parse_constant=reject_constant,
            )
        except (UnicodeError, ValueError, RecursionError):
            raise ParseError("Invalid JSON request.") from None
        return data


class SafeAIInputSerializer(StrictInputSerializer):
    """Reuse strict-field convention without reflecting unknown field names."""

    def to_internal_value(self, data):
        if not isinstance(data, Mapping) or any(
            type(key) is not str or key not in self.fields for key in data
        ):
            raise serializers.ValidationError({
                "non_field_errors": ["Only the documented request fields are allowed."],
            })
        return super().to_internal_value(data)


class GenerateProposalSerializer(SafeAIInputSerializer):
    scenario_id = serializers.CharField(max_length=80, trim_whitespace=False)

    def to_internal_value(self, data):
        if isinstance(data, Mapping) and "scenario_id" in data and type(data["scenario_id"]) is not str:
            raise serializers.ValidationError({"scenario_id": ["A scenario identifier is required."]})
        return super().to_internal_value(data)


class ConfirmProposalSerializer(SafeAIInputSerializer):
    proposal_revision = serializers.IntegerField(min_value=1)
    confirmed = serializers.BooleanField()
    payload = serializers.JSONField()

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            if "proposal_revision" in data and type(data["proposal_revision"]) is not int:
                raise serializers.ValidationError({"proposal_revision": ["A positive integer is required."]})
            if "confirmed" in data and (type(data["confirmed"]) is not bool or data["confirmed"] is not True):
                raise serializers.ValidationError({"confirmed": ["Explicit confirmation is required."]})
            if "payload" in data and type(data["payload"]) is not dict:
                raise serializers.ValidationError({"payload": ["A task-plan object is required."]})
        return super().to_internal_value(data)


class FixtureGenerationMinuteThrottle(UserRateThrottle):
    """Process-cache attempt limit, not a shared multi-worker quota guarantee."""

    scope = "ai_fixture_generation_minute"
    rate = "3/minute"


class FixtureGenerationDayThrottle(UserRateThrottle):
    scope = "ai_fixture_generation_day"
    rate = "20/day"


class ProposalApiMixin(TenantApiViewMixin):
    permission_classes = (CanManageWorkspaceTasks,)
    parser_classes = (BoundedStrictJSONParser,)

    def handle_exception(self, exc):
        if isinstance(exc, AIError):
            code = exc.code.value
            code_status = {
                "AI_DISABLED": status.HTTP_503_SERVICE_UNAVAILABLE,
                "PERMISSION_DENIED": status.HTTP_403_FORBIDDEN,
                "NOT_FOUND": status.HTTP_404_NOT_FOUND,
                "IDEMPOTENCY_CONFLICT": status.HTTP_409_CONFLICT,
                "ALREADY_CONFIRMED": status.HTTP_409_CONFLICT,
                "STALE_PROPOSAL": status.HTTP_409_CONFLICT,
                "STALE_CONTEXT": status.HTTP_409_CONFLICT,
                "EXPIRED": status.HTTP_410_GONE,
                "RECOVERY_EXPIRED": status.HTTP_410_GONE,
                "RATE_LIMITED": status.HTTP_429_TOO_MANY_REQUESTS,
                "BUDGET_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
                "PROVIDER_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
                "PROVIDER_TIMEOUT": status.HTTP_504_GATEWAY_TIMEOUT,
                "INVALID_PROVIDER_RESPONSE": status.HTTP_502_BAD_GATEWAY,
            }
            public = exc.as_public_error()
            response = Response({
                "detail": public["message"],
                "code": public["code"],
                "fields": {name: [public["message"]] for name in public["fields"]},
            }, status=code_status.get(code, status.HTTP_400_BAD_REQUEST))
            return response
        return super().handle_exception(exc)

    def idempotency_key(self):
        raw = self.request.headers.get("Idempotency-Key")
        try:
            if type(raw) is not str or len(raw) > 64:
                raise ValueError()
            return UUID(raw)
        except (ValueError, TypeError, AttributeError):
            raise serializers.ValidationError({
                "idempotency_key": ["A valid Idempotency-Key UUID header is required."],
            }) from None

    def scope_kwargs(self):
        return {
            "actor": self.request.user,
            "profile_id": self.kwargs["profile_id"],
            "workspace_id": self.kwargs["workspace_id"],
        }


@method_decorator(never_cache, name="dispatch")
@method_decorator(sensitive_post_parameters("payload"), name="dispatch")
class ProposalGenerateView(ProposalApiMixin, APIView):
    http_method_names = ("post", "options")
    throttle_classes = (FixtureGenerationMinuteThrottle, FixtureGenerationDayThrottle)

    def post(self, request, **kwargs):
        serializer = GenerateProposalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proposal, replayed = durable_services.generate_proposal(
            **self.scope_kwargs(), idempotency_key=self.idempotency_key(),
            **serializer.validated_data,
        )
        return Response(durable_services.serialize_proposal(proposal), status=(
            status.HTTP_200_OK if replayed else status.HTTP_201_CREATED
        ))


@method_decorator(never_cache, name="dispatch")
class ProposalDetailView(ProposalApiMixin, APIView):
    http_method_names = ("get", "head", "options")

    def get(self, request, **kwargs):
        proposal = durable_services.retrieve_proposal(
            **self.scope_kwargs(), proposal_id=kwargs["proposal_id"],
        )
        return Response(durable_services.serialize_proposal(proposal))


@method_decorator(never_cache, name="dispatch")
@method_decorator(sensitive_post_parameters("payload"), name="dispatch")
class ProposalConfirmView(ProposalApiMixin, APIView):
    http_method_names = ("post", "options")

    def post(self, request, **kwargs):
        serializer = ConfirmProposalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proposal, replayed = durable_services.confirm_proposal(
            **self.scope_kwargs(), proposal_id=kwargs["proposal_id"],
            idempotency_key=self.idempotency_key(), **serializer.validated_data,
        )
        return Response(durable_services.serialize_proposal(proposal), status=(
            status.HTTP_200_OK if replayed else status.HTTP_201_CREATED
        ))
