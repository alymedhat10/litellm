from typing import Any, Dict, List, Optional, Union

from litellm._logging import verbose_logger
from litellm.integrations.custom_logger import CustomLogger
from litellm.types.guardrails import GuardrailEventHooks


class CustomGuardrail(CustomLogger):

    def __init__(
        self,
        guardrail_name: Optional[str] = None,
        supported_event_hooks: Optional[List[GuardrailEventHooks]] = None,
        event_hook: Optional[GuardrailEventHooks] = None,
        **kwargs,
    ):
        self.guardrail_name = guardrail_name
        self.supported_event_hooks = supported_event_hooks
        self.event_hook: Optional[GuardrailEventHooks] = event_hook

        if supported_event_hooks:
            ## validate event_hook is in supported_event_hooks
            if event_hook and event_hook not in supported_event_hooks:
                raise ValueError(
                    f"Event hook {event_hook} is not in the supported event hooks {supported_event_hooks}"
                )
        super().__init__(**kwargs)

    def get_guardrail_from_metadata(
        self, data: dict
    ) -> Union[List[str], List[Dict[str, Any]]]:
        """
        Returns the guardrail(s) to be run from the metadata
        """
        metadata = data.get("metadata") or {}
        requested_guardrails = metadata.get("guardrails") or []
        return requested_guardrails

    def _guardrail_is_in_requested_guardrails(
        self,
        requested_guardrails: Union[List[str], List[Dict[str, Any]]],
    ) -> bool:
        for _guardrail in requested_guardrails:
            if isinstance(_guardrail, dict):
                if self.guardrail_name in _guardrail:
                    return True
            elif isinstance(_guardrail, str):
                if self.guardrail_name == _guardrail:
                    return True
        return False

    def should_run_guardrail(self, data, event_type: GuardrailEventHooks) -> bool:
        requested_guardrails = self.get_guardrail_from_metadata(data)

        verbose_logger.debug(
            "inside should_run_guardrail for guardrail=%s event_type= %s guardrail_supported_event_hooks= %s requested_guardrails= %s",
            self.guardrail_name,
            event_type,
            self.event_hook,
            requested_guardrails,
        )

        # logging only guards should not run here - there are run only in litellm_logging.py
        if event_type.value == "logging_only":
            return False

        # check if self.guardrail_name is in requested_guardrails for the request
        if self._guardrail_is_in_requested_guardrails(requested_guardrails) is not True:
            return False

        if self.event_hook and self.event_hook != event_type.value:
            return False

        return True

    def get_guardrail_dynamic_request_body_params(self, data: dict) -> dict:
        """
        Returns `extra_body` to be added to the request body for the Guardrail API call

        ```
        [{"lakera_guard": {"extra_body": {"foo": "bar"}}}]
        ```

        Will return: for guardrail=`lakera-guard`:
        {
            "foo": "bar"
        }
        """
        requested_guardrails = self.get_guardrail_from_metadata(data)

        # Look for the guardrail configuration matching self.guardrail_name
        for guardrail in requested_guardrails:
            if isinstance(guardrail, dict) and self.guardrail_name in guardrail:
                # Get the configuration for this guardrail
                guardrail_config = guardrail[self.guardrail_name]
                # Return the extra_body if it exists, otherwise empty dict
                return guardrail_config.get("extra_body", {})

        return {}
