from typing import List, Optional, Tuple

import litellm
from litellm._logging import verbose_logger
from litellm.litellm_core_utils.prompt_templates.common_utils import (
    _audio_or_image_in_message_content,
    convert_content_list_to_str,
)
from litellm.litellm_core_utils.prompt_templates.factory import (
    stringify_json_tool_call_content,
)
from litellm.llms.openai.openai import OpenAIConfig
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import ProviderField


class AzureAIStudioConfig(OpenAIConfig):
    def get_required_params(self) -> List[ProviderField]:
        """For a given provider, return it's required fields with a description"""
        return [
            ProviderField(
                field_name="api_key",
                field_type="string",
                field_description="Your Azure AI Studio API Key.",
                field_value="zEJ...",
            ),
            ProviderField(
                field_name="api_base",
                field_type="string",
                field_description="Your Azure AI Studio API Base.",
                field_value="https://Mistral-serverless.",
            ),
        ]

    def _transform_messages(
        self,
        messages: List[AllMessageValues],
        model: str,
    ) -> List:
        """
        - Azure AI Studio doesn't support content as a list. This handles:
            1. Transforms list content to a string.
            2. If message contains an image or audio, send as is (user-intended)
        """
        ## FOR COHERE
        if "command-r" in model:  # make sure tool call in messages are str
            messages = stringify_json_tool_call_content(messages=messages)

        for message in messages:

            # Do nothing if the message contains an image or audio
            if _audio_or_image_in_message_content(message):
                continue

            texts = convert_content_list_to_str(message=message)
            if texts:
                message["content"] = texts
        return messages

    def _is_azure_openai_model(self, model: str) -> bool:
        try:
            if "/" in model:
                model = model.split("/", 1)[1]
            if (
                model in litellm.open_ai_chat_completion_models
                or model in litellm.open_ai_text_completion_models
                or model in litellm.open_ai_embedding_models
            ):
                return True
        except Exception:
            return False
        return False

    def _get_openai_compatible_provider_info(
        self,
        model: str,
        api_base: Optional[str],
        api_key: Optional[str],
        custom_llm_provider: str,
    ) -> Tuple[Optional[str], Optional[str], str]:
        api_base = api_base or get_secret_str("AZURE_AI_API_BASE")
        dynamic_api_key = api_key or get_secret_str("AZURE_AI_API_KEY")

        if self._is_azure_openai_model(model=model):
            verbose_logger.debug(
                "Model={} is Azure OpenAI model. Setting custom_llm_provider='azure'.".format(
                    model
                )
            )
            custom_llm_provider = "azure"
        return api_base, dynamic_api_key, custom_llm_provider

    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        if headers is None:
            headers = {
                "Content-Type": "application/json",
            }

        # set 'api-key' in headers if api base is 'services.azure.ai'
        if api_base and "services.ai.azure" in api_base:
            headers["api-key"] = api_key
        else:
            headers["Authorization"] = "Bearer {}".format(api_key)
        return headers
