from typing import List, Literal, Optional, Tuple, Union, cast

import litellm
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import AllMessageValues, ChatCompletionImageObject

from ...openai.chat.gpt_transformation import OpenAIGPTConfig


class FireworksAIConfig(OpenAIGPTConfig):
    """
    Reference: https://docs.fireworks.ai/api-reference/post-chatcompletions

    The class `FireworksAIConfig` provides configuration for the Fireworks's Chat Completions API interface. Below are the parameters:
    """

    tools: Optional[list] = None
    tool_choice: Optional[Union[str, dict]] = None
    max_tokens: Optional[int] = None
    temperature: Optional[int] = None
    top_p: Optional[int] = None
    top_k: Optional[int] = None
    frequency_penalty: Optional[int] = None
    presence_penalty: Optional[int] = None
    n: Optional[int] = None
    stop: Optional[Union[str, list]] = None
    response_format: Optional[dict] = None
    user: Optional[str] = None
    logprobs: Optional[int] = None

    # Non OpenAI parameters - Fireworks AI only params
    prompt_truncate_length: Optional[int] = None
    context_length_exceeded_behavior: Optional[Literal["error", "truncate"]] = None

    def __init__(
        self,
        tools: Optional[list] = None,
        tool_choice: Optional[Union[str, dict]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[int] = None,
        top_p: Optional[int] = None,
        top_k: Optional[int] = None,
        frequency_penalty: Optional[int] = None,
        presence_penalty: Optional[int] = None,
        n: Optional[int] = None,
        stop: Optional[Union[str, list]] = None,
        response_format: Optional[dict] = None,
        user: Optional[str] = None,
        logprobs: Optional[int] = None,
        prompt_truncate_length: Optional[int] = None,
        context_length_exceeded_behavior: Optional[Literal["error", "truncate"]] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

    def get_supported_openai_params(self, model: str):
        return [
            "stream",
            "tools",
            "tool_choice",
            "max_completion_tokens",
            "max_tokens",
            "temperature",
            "top_p",
            "top_k",
            "frequency_penalty",
            "presence_penalty",
            "n",
            "stop",
            "response_format",
            "user",
            "logprobs",
            "prompt_truncate_length",
            "context_length_exceeded_behavior",
        ]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:

        supported_openai_params = self.get_supported_openai_params(model=model)
        for param, value in non_default_params.items():
            if param == "tool_choice":
                if value == "required":
                    # relevant issue: https://github.com/BerriAI/litellm/issues/4416
                    optional_params["tool_choice"] = "any"
                else:
                    # pass through the value of tool choice
                    optional_params["tool_choice"] = value
            elif (
                param == "response_format" and value.get("type", None) == "json_schema"
            ):
                optional_params["response_format"] = {
                    "type": "json_object",
                    "schema": value["json_schema"]["schema"],
                }
            elif param == "max_completion_tokens":
                optional_params["max_tokens"] = value
            elif param in supported_openai_params:
                if value is not None:
                    optional_params[param] = value
        return optional_params

    def _add_transform_inline_image_block(
        self,
        content: ChatCompletionImageObject,
        model: str,
        disable_add_transform_inline_image_block: Optional[bool],
    ) -> ChatCompletionImageObject:
        """
        Add transform_inline to the image_url (allows non-vision models to parse documents/images/etc.)
        - ignore if model is a vision model
        - ignore if user has disabled this feature
        """
        if (
            "vision" in model or disable_add_transform_inline_image_block
        ):  # allow user to toggle this feature.
            return content
        if isinstance(content["image_url"], str):
            content["image_url"] = f"{content['image_url']}#transform=inline"
        elif isinstance(content["image_url"], dict):
            content["image_url"][
                "url"
            ] = f"{content['image_url']['url']}#transform=inline"
        return content

    def _transform_messages_helper(
        self, messages: List[AllMessageValues], model: str, litellm_params: dict
    ) -> List[AllMessageValues]:
        """
        Add 'transform=inline' to the url of the image_url
        """
        disable_add_transform_inline_image_block = cast(
            Optional[bool],
            litellm_params.get(
                "disable_add_transform_inline_image_block",
                litellm.disable_add_transform_inline_image_block,
            ),
        )
        for message in messages:
            if message["role"] == "user":
                _message_content = message.get("content")
                if _message_content is not None and isinstance(_message_content, list):
                    for content in _message_content:
                        if content["type"] == "image_url":
                            content = self._add_transform_inline_image_block(
                                content=content,
                                model=model,
                                disable_add_transform_inline_image_block=disable_add_transform_inline_image_block,
                            )
        return messages

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        if not model.startswith("accounts/"):
            model = f"accounts/fireworks/models/{model}"
        messages = self._transform_messages_helper(
            messages=messages, model=model, litellm_params=litellm_params
        )
        return super().transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            headers=headers,
        )

    def _get_openai_compatible_provider_info(
        self, model: str, api_base: Optional[str], api_key: Optional[str]
    ) -> Tuple[str, Optional[str], Optional[str]]:
        api_base = (
            api_base
            or get_secret_str("FIREWORKS_API_BASE")
            or "https://api.fireworks.ai/inference/v1"
        )  # type: ignore
        dynamic_api_key = api_key or (
            get_secret_str("FIREWORKS_API_KEY")
            or get_secret_str("FIREWORKS_AI_API_KEY")
            or get_secret_str("FIREWORKSAI_API_KEY")
            or get_secret_str("FIREWORKS_AI_TOKEN")
        )
        return model, api_base, dynamic_api_key
