#### What this tests ####
#    This tests if get_optional_params works as expected
import asyncio
import inspect
import os
import sys
import time
import traceback

import pytest

sys.path.insert(0, os.path.abspath("../.."))
from unittest.mock import MagicMock, patch

import litellm
from litellm.litellm_core_utils.prompt_templates.factory import map_system_message_pt
from litellm.types.completion import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from litellm.utils import (
    get_optional_params,
    get_optional_params_embeddings,
    get_optional_params_image_gen,
)

## get_optional_params_embeddings
### Models: OpenAI, Azure, Bedrock
### Scenarios: w/ optional params + litellm.drop_params = True


def test_supports_system_message():
    """
    Check if litellm.completion(...,supports_system_message=False)
    """
    messages = [
        ChatCompletionSystemMessageParam(role="system", content="Listen here!"),
        ChatCompletionUserMessageParam(role="user", content="Hello there!"),
    ]

    new_messages = map_system_message_pt(messages=messages)

    assert len(new_messages) == 1
    assert new_messages[0]["role"] == "user"

    ## confirm you can make a openai call with this param

    response = litellm.completion(
        model="gpt-3.5-turbo", messages=new_messages, supports_system_message=False
    )

    assert isinstance(response, litellm.ModelResponse)


@pytest.mark.parametrize(
    "stop_sequence, expected_count", [("\n", 0), (["\n"], 0), (["finish_reason"], 1)]
)
def test_anthropic_optional_params(stop_sequence, expected_count):
    """
    Test if whitespace character optional param is dropped by anthropic
    """
    litellm.drop_params = True
    optional_params = get_optional_params(
        model="claude-3", custom_llm_provider="anthropic", stop=stop_sequence
    )
    assert len(optional_params) == expected_count


def test_bedrock_optional_params_embeddings():
    litellm.drop_params = True
    optional_params = get_optional_params_embeddings(
        model="", user="John", encoding_format=None, custom_llm_provider="bedrock"
    )
    assert len(optional_params) == 0


@pytest.mark.parametrize(
    "model",
    [
        "us.anthropic.claude-3-haiku-20240307-v1:0",
        "us.meta.llama3-2-11b-instruct-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
    ],
)
def test_bedrock_optional_params_completions(model):
    tools = [
        {
            "type": "function",
            "function": {
                "name": "structure_output",
                "description": "Send structured output back to the user",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reasoning": {"type": "string"},
                        "sentiment": {"type": "string"},
                    },
                    "required": ["reasoning", "sentiment"],
                    "additionalProperties": False,
                },
                "additionalProperties": False,
            },
        }
    ]
    optional_params = get_optional_params(
        model=model,
        max_tokens=10,
        temperature=0.1,
        tools=tools,
        custom_llm_provider="bedrock",
    )
    print(f"optional_params: {optional_params}")
    assert len(optional_params) == 4
    assert optional_params == {
        "maxTokens": 10,
        "stream": False,
        "temperature": 0.1,
        "tools": tools,
    }


@pytest.mark.parametrize(
    "model",
    [
        "bedrock/amazon.titan-large",
        "bedrock/meta.llama3-2-11b-instruct-v1:0",
        "bedrock/ai21.j2-ultra-v1",
        "bedrock/cohere.command-nightly",
        "bedrock/mistral.mistral-7b",
    ],
)
def test_bedrock_optional_params_simple(model):
    litellm.drop_params = True
    get_optional_params(
        model=model,
        max_tokens=10,
        temperature=0.1,
        custom_llm_provider="bedrock",
    )


@pytest.mark.parametrize(
    "model, expected_dimensions, dimensions_kwarg",
    [
        ("bedrock/amazon.titan-embed-text-v1", False, None),
        ("bedrock/amazon.titan-embed-image-v1", True, "embeddingConfig"),
        ("bedrock/amazon.titan-embed-text-v2:0", True, "dimensions"),
        ("bedrock/cohere.embed-multilingual-v3", False, None),
    ],
)
def test_bedrock_optional_params_embeddings_dimension(
    model, expected_dimensions, dimensions_kwarg
):
    litellm.drop_params = True
    optional_params = get_optional_params_embeddings(
        model=model,
        user="John",
        encoding_format=None,
        dimensions=20,
        custom_llm_provider="bedrock",
    )
    if expected_dimensions:
        assert len(optional_params) == 1
    else:
        assert len(optional_params) == 0

    if dimensions_kwarg is not None:
        assert dimensions_kwarg in optional_params


def test_google_ai_studio_optional_params_embeddings():
    optional_params = get_optional_params_embeddings(
        model="",
        user="John",
        encoding_format=None,
        custom_llm_provider="gemini",
        drop_params=True,
    )
    assert len(optional_params) == 0


def test_openai_optional_params_embeddings():
    litellm.drop_params = True
    optional_params = get_optional_params_embeddings(
        model="", user="John", encoding_format=None, custom_llm_provider="openai"
    )
    assert len(optional_params) == 1
    assert optional_params["user"] == "John"


def test_azure_optional_params_embeddings():
    litellm.drop_params = True
    optional_params = get_optional_params_embeddings(
        model="chatgpt-v-2",
        user="John",
        encoding_format=None,
        custom_llm_provider="azure",
    )
    assert len(optional_params) == 1
    assert optional_params["user"] == "John"


def test_databricks_optional_params():
    litellm.drop_params = True
    optional_params = get_optional_params(
        model="",
        user="John",
        custom_llm_provider="databricks",
        max_tokens=10,
        temperature=0.2,
        stream=True,
    )
    print(f"optional_params: {optional_params}")
    assert len(optional_params) == 3
    assert "user" not in optional_params


def test_gemini_optional_params():
    litellm.drop_params = True
    optional_params = get_optional_params(
        model="",
        custom_llm_provider="gemini",
        max_tokens=10,
        frequency_penalty=10,
    )
    print(f"optional_params: {optional_params}")
    assert len(optional_params) == 1
    assert "frequency_penalty" not in optional_params


def test_azure_ai_mistral_optional_params():
    litellm.drop_params = True
    optional_params = get_optional_params(
        model="mistral-large-latest",
        user="John",
        custom_llm_provider="openai",
        max_tokens=10,
        temperature=0.2,
    )
    assert "user" not in optional_params


def test_vertex_ai_llama_3_optional_params():
    litellm.vertex_llama3_models = ["meta/llama3-405b-instruct-maas"]
    litellm.drop_params = True
    optional_params = get_optional_params(
        model="meta/llama3-405b-instruct-maas",
        user="John",
        custom_llm_provider="vertex_ai",
        max_tokens=10,
        temperature=0.2,
    )
    assert "user" not in optional_params


def test_vertex_ai_mistral_optional_params():
    litellm.vertex_mistral_models = ["mistral-large@2407"]
    litellm.drop_params = True
    optional_params = get_optional_params(
        model="mistral-large@2407",
        user="John",
        custom_llm_provider="vertex_ai",
        max_tokens=10,
        temperature=0.2,
    )
    assert "user" not in optional_params
    assert "max_tokens" in optional_params
    assert "temperature" in optional_params


def test_azure_gpt_optional_params_gpt_vision():
    # for OpenAI, Azure all extra params need to get passed as extra_body to OpenAI python. We assert we actually set extra_body here
    optional_params = litellm.utils.get_optional_params(
        model="",
        user="John",
        custom_llm_provider="azure",
        max_tokens=10,
        temperature=0.2,
        enhancements={"ocr": {"enabled": True}, "grounding": {"enabled": True}},
        dataSources=[
            {
                "type": "AzureComputerVision",
                "parameters": {
                    "endpoint": "<your_computer_vision_endpoint>",
                    "key": "<your_computer_vision_key>",
                },
            }
        ],
    )

    print(optional_params)
    assert optional_params["max_tokens"] == 10
    assert optional_params["temperature"] == 0.2
    assert optional_params["extra_body"] == {
        "enhancements": {"ocr": {"enabled": True}, "grounding": {"enabled": True}},
        "dataSources": [
            {
                "type": "AzureComputerVision",
                "parameters": {
                    "endpoint": "<your_computer_vision_endpoint>",
                    "key": "<your_computer_vision_key>",
                },
            }
        ],
    }


# test_azure_gpt_optional_params_gpt_vision()


def test_azure_gpt_optional_params_gpt_vision_with_extra_body():
    # if user passes extra_body, we should not over write it, we should pass it along to OpenAI python
    optional_params = litellm.utils.get_optional_params(
        model="",
        user="John",
        custom_llm_provider="azure",
        max_tokens=10,
        temperature=0.2,
        extra_body={
            "meta": "hi",
        },
        enhancements={"ocr": {"enabled": True}, "grounding": {"enabled": True}},
        dataSources=[
            {
                "type": "AzureComputerVision",
                "parameters": {
                    "endpoint": "<your_computer_vision_endpoint>",
                    "key": "<your_computer_vision_key>",
                },
            }
        ],
    )

    print(optional_params)
    assert optional_params["max_tokens"] == 10
    assert optional_params["temperature"] == 0.2
    assert optional_params["extra_body"] == {
        "enhancements": {"ocr": {"enabled": True}, "grounding": {"enabled": True}},
        "dataSources": [
            {
                "type": "AzureComputerVision",
                "parameters": {
                    "endpoint": "<your_computer_vision_endpoint>",
                    "key": "<your_computer_vision_key>",
                },
            }
        ],
        "meta": "hi",
    }


# test_azure_gpt_optional_params_gpt_vision_with_extra_body()


def test_openai_extra_headers():
    optional_params = litellm.utils.get_optional_params(
        model="",
        user="John",
        custom_llm_provider="openai",
        max_tokens=10,
        temperature=0.2,
        extra_headers={"AI-Resource Group": "ishaan-resource"},
    )

    print(optional_params)
    assert optional_params["max_tokens"] == 10
    assert optional_params["temperature"] == 0.2
    assert optional_params["extra_headers"] == {"AI-Resource Group": "ishaan-resource"}


@pytest.mark.parametrize(
    "api_version",
    [
        "2024-02-01",
        "2024-07-01",  # potential future version with tool_choice="required" supported
        "2023-07-01-preview",
        "2024-03-01-preview",
    ],
)
def test_azure_tool_choice(api_version):
    """
    Test azure tool choice on older + new version
    """
    litellm.drop_params = True
    optional_params = litellm.utils.get_optional_params(
        model="chatgpt-v-2",
        user="John",
        custom_llm_provider="azure",
        max_tokens=10,
        temperature=0.2,
        extra_headers={"AI-Resource Group": "ishaan-resource"},
        tool_choice="required",
        api_version=api_version,
    )

    print(f"{optional_params}")
    if api_version == "2024-07-01":
        assert optional_params["tool_choice"] == "required"
    else:
        assert (
            "tool_choice" not in optional_params
        ), "tool choice should not be present. Got - tool_choice={} for api version={}".format(
            optional_params["tool_choice"], api_version
        )


@pytest.mark.parametrize("drop_params", [True, False, None])
def test_dynamic_drop_params(drop_params):
    """
    Make a call to cohere w/ drop params = True vs. false.
    """
    if drop_params is True:
        optional_params = litellm.utils.get_optional_params(
            model="command-r",
            custom_llm_provider="cohere",
            response_format={"type": "json"},
            drop_params=drop_params,
        )
    else:
        try:
            optional_params = litellm.utils.get_optional_params(
                model="command-r",
                custom_llm_provider="cohere",
                response_format={"type": "json"},
                drop_params=drop_params,
            )
            pytest.fail("Expected to fail")
        except Exception as e:
            pass


def test_dynamic_drop_params_e2e():
    with patch(
        "litellm.llms.custom_httpx.http_handler.HTTPHandler.post", new=MagicMock()
    ) as mock_response:
        try:
            response = litellm.completion(
                model="command-r",
                messages=[{"role": "user", "content": "Hey, how's it going?"}],
                response_format={"key": "value"},
                drop_params=True,
            )
        except Exception as e:
            pass

        mock_response.assert_called_once()
        print(mock_response.call_args.kwargs["data"])
        assert "response_format" not in mock_response.call_args.kwargs["data"]


@pytest.mark.parametrize(
    "model, provider, should_drop",
    [("command-r", "cohere", True), ("gpt-3.5-turbo", "openai", False)],
)
def test_drop_params_parallel_tool_calls(model, provider, should_drop):
    """
    https://github.com/BerriAI/litellm/issues/4584
    """
    response = litellm.utils.get_optional_params(
        model=model,
        custom_llm_provider=provider,
        response_format={"type": "json"},
        parallel_tool_calls=True,
        drop_params=True,
    )

    print(response)

    if should_drop:
        assert "response_format" not in response
        assert "parallel_tool_calls" not in response
    else:
        assert "response_format" in response
        assert "parallel_tool_calls" in response


def test_dynamic_drop_params_parallel_tool_calls():
    """
    https://github.com/BerriAI/litellm/issues/4584
    """
    with patch(
        "litellm.llms.custom_httpx.http_handler.HTTPHandler.post", new=MagicMock()
    ) as mock_response:
        try:
            response = litellm.completion(
                model="command-r",
                messages=[{"role": "user", "content": "Hey, how's it going?"}],
                parallel_tool_calls=True,
                drop_params=True,
            )
        except Exception as e:
            pass

        mock_response.assert_called_once()
        print(mock_response.call_args.kwargs["data"])
        assert "parallel_tool_calls" not in mock_response.call_args.kwargs["data"]


@pytest.mark.parametrize("drop_params", [True, False, None])
def test_dynamic_drop_additional_params(drop_params):
    """
    Make a call to cohere, dropping 'response_format' specifically
    """
    if drop_params is True:
        optional_params = litellm.utils.get_optional_params(
            model="command-r",
            custom_llm_provider="cohere",
            response_format={"type": "json"},
            additional_drop_params=["response_format"],
        )
    else:
        try:
            optional_params = litellm.utils.get_optional_params(
                model="command-r",
                custom_llm_provider="cohere",
                response_format={"type": "json"},
            )
            pytest.fail("Expected to fail")
        except Exception as e:
            pass


def test_dynamic_drop_additional_params_stream_options():
    """
    Make a call to vertex ai, dropping 'stream_options' specifically
    """
    optional_params = litellm.utils.get_optional_params(
        model="mistral-large-2411@001",
        custom_llm_provider="vertex_ai",
        stream_options={"include_usage": True},
        additional_drop_params=["stream_options"],
    )

    assert "stream_options" not in optional_params


def test_dynamic_drop_additional_params_e2e():
    with patch(
        "litellm.llms.custom_httpx.http_handler.HTTPHandler.post", new=MagicMock()
    ) as mock_response:
        try:
            response = litellm.completion(
                model="command-r",
                messages=[{"role": "user", "content": "Hey, how's it going?"}],
                response_format={"key": "value"},
                additional_drop_params=["response_format"],
            )
        except Exception as e:
            pass

        mock_response.assert_called_once()
        print(mock_response.call_args.kwargs["data"])
        assert "response_format" not in mock_response.call_args.kwargs["data"]
        assert "additional_drop_params" not in mock_response.call_args.kwargs["data"]


def test_get_optional_params_image_gen():
    response = litellm.utils.get_optional_params_image_gen(
        aws_region_name="us-east-1", custom_llm_provider="openai"
    )

    print(response)

    assert "aws_region_name" not in response
    response = litellm.utils.get_optional_params_image_gen(
        aws_region_name="us-east-1", custom_llm_provider="bedrock"
    )

    print(response)

    assert "aws_region_name" in response


def test_bedrock_optional_params_embeddings_provider_specific_params():
    optional_params = get_optional_params_embeddings(
        model="my-custom-model",
        custom_llm_provider="huggingface",
        wait_for_model=True,
    )
    assert len(optional_params) == 1


def test_get_optional_params_num_retries():
    """
    Relevant issue - https://github.com/BerriAI/litellm/issues/5124
    """
    with patch("litellm.main.get_optional_params", new=MagicMock()) as mock_client:
        _ = litellm.completion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello world"}],
            num_retries=10,
        )

        mock_client.assert_called()

        print(f"mock_client.call_args: {mock_client.call_args}")
        assert mock_client.call_args.kwargs["max_retries"] == 10


@pytest.mark.parametrize(
    "provider",
    [
        "vertex_ai",
        "vertex_ai_beta",
    ],
)
def test_vertex_safety_settings(provider):
    litellm.vertex_ai_safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE",
        },
    ]

    optional_params = get_optional_params(
        model="gemini-1.5-pro", custom_llm_provider=provider
    )
    assert len(optional_params) == 1


@pytest.mark.parametrize(
    "model, provider, expectedAddProp",
    [("gemini-1.5-pro", "vertex_ai_beta", False), ("gpt-3.5-turbo", "openai", True)],
)
def test_parse_additional_properties_json_schema(model, provider, expectedAddProp):
    optional_params = get_optional_params(
        model=model,
        custom_llm_provider=provider,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "math_reasoning",
                "schema": {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "explanation": {"type": "string"},
                                    "output": {"type": "string"},
                                },
                                "required": ["explanation", "output"],
                                "additionalProperties": False,
                            },
                        },
                        "final_answer": {"type": "string"},
                    },
                    "required": ["steps", "final_answer"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
    )

    print(optional_params)

    if provider == "vertex_ai_beta":
        schema = optional_params["response_schema"]
    elif provider == "openai":
        schema = optional_params["response_format"]["json_schema"]["schema"]
    assert ("additionalProperties" in schema) == expectedAddProp


def test_o1_model_params():
    optional_params = get_optional_params(
        model="o1-preview-2024-09-12",
        custom_llm_provider="openai",
        seed=10,
        user="John",
    )
    assert optional_params["seed"] == 10
    assert optional_params["user"] == "John"


def test_azure_o1_model_params():
    optional_params = get_optional_params(
        model="o1-preview",
        custom_llm_provider="azure",
        seed=10,
        user="John",
    )
    assert optional_params["seed"] == 10
    assert optional_params["user"] == "John"


@pytest.mark.parametrize(
    "temperature, expected_error",
    [(0.2, True), (1, False), (0, True)],
)
@pytest.mark.parametrize("provider", ["openai", "azure"])
def test_o1_model_temperature_params(provider, temperature, expected_error):
    if expected_error:
        with pytest.raises(litellm.UnsupportedParamsError):
            get_optional_params(
                model="o1-preview",
                custom_llm_provider=provider,
                temperature=temperature,
            )
    else:
        get_optional_params(
            model="o1-preview-2024-09-12",
            custom_llm_provider="openai",
            temperature=temperature,
        )


def test_unmapped_gemini_model_params():
    """
    Test if unmapped gemini model optional params are translated correctly
    """
    optional_params = get_optional_params(
        model="gemini-new-model",
        custom_llm_provider="vertex_ai",
        stop="stop_word",
    )
    assert optional_params["stop_sequences"] == ["stop_word"]


def _check_additional_properties(schema):
    if isinstance(schema, dict):
        # Remove the 'additionalProperties' key if it exists and is set to False
        if "additionalProperties" in schema or "strict" in schema:
            raise ValueError(
                "additionalProperties and strict should not be in the schema"
            )

        # Recursively process all dictionary values
        for key, value in schema.items():
            _check_additional_properties(value)

    elif isinstance(schema, list):
        # Recursively process all items in the list
        for item in schema:
            _check_additional_properties(item)

    return schema


@pytest.mark.parametrize(
    "provider, model",
    [
        ("hosted_vllm", "my-vllm-model"),
        ("gemini", "gemini-1.5-pro"),
        ("vertex_ai", "gemini-1.5-pro"),
    ],
)
def test_drop_nested_params_add_prop_and_strict(provider, model):
    """
    Relevant issue - https://github.com/BerriAI/litellm/issues/5288

    Relevant issue - https://github.com/BerriAI/litellm/issues/6136
    """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "structure_output",
                "description": "Send structured output back to the user",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reasoning": {"type": "string"},
                        "sentiment": {"type": "string"},
                    },
                    "required": ["reasoning", "sentiment"],
                    "additionalProperties": False,
                },
                "additionalProperties": False,
            },
        }
    ]
    tool_choice = {"type": "function", "function": {"name": "structure_output"}}
    optional_params = get_optional_params(
        model=model,
        custom_llm_provider=provider,
        temperature=0.2,
        tools=tools,
        tool_choice=tool_choice,
        additional_drop_params=[
            ["tools", "function", "strict"],
            ["tools", "function", "additionalProperties"],
        ],
    )

    _check_additional_properties(optional_params["tools"])


def test_hosted_vllm_tool_param():
    """
    Relevant issue - https://github.com/BerriAI/litellm/issues/6228
    """
    optional_params = get_optional_params(
        model="my-vllm-model",
        custom_llm_provider="hosted_vllm",
        temperature=0.2,
        tools=None,
        tool_choice=None,
    )
    assert "tools" not in optional_params
    assert "tool_choice" not in optional_params


def test_unmapped_vertex_anthropic_model():
    optional_params = get_optional_params(
        model="claude-3-5-sonnet-v250@20241022",
        custom_llm_provider="vertex_ai",
        max_retries=10,
    )
    assert "max_retries" not in optional_params


@pytest.mark.parametrize("provider", ["anthropic", "vertex_ai"])
def test_anthropic_parallel_tool_calls(provider):
    optional_params = get_optional_params(
        model="claude-3-5-sonnet-v250@20241022",
        custom_llm_provider=provider,
        parallel_tool_calls=True,
    )
    print(f"optional_params: {optional_params}")
    assert optional_params["tool_choice"]["disable_parallel_tool_use"] is False


def test_anthropic_computer_tool_use():
    tools = [
        {
            "type": "computer_20241022",
            "function": {
                "name": "computer",
                "parameters": {
                    "display_height_px": 100,
                    "display_width_px": 100,
                    "display_number": 1,
                },
            },
        }
    ]

    optional_params = get_optional_params(
        model="claude-3-5-sonnet-v250@20241022",
        custom_llm_provider="anthropic",
        tools=tools,
    )
    assert optional_params["tools"][0]["type"] == "computer_20241022"
    assert optional_params["tools"][0]["display_height_px"] == 100
    assert optional_params["tools"][0]["display_width_px"] == 100
    assert optional_params["tools"][0]["display_number"] == 1


def test_vertex_schema_field():
    tools = [
        {
            "type": "function",
            "function": {
                "name": "json",
                "description": "Respond with a JSON object.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "thinking": {
                            "type": "string",
                            "description": "Your internal thoughts on different problem details given the guidance.",
                        },
                        "problems": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "icon": {
                                        "type": "string",
                                        "enum": [
                                            "BarChart2",
                                            "Bell",
                                        ],
                                        "description": "The name of a Lucide icon to display",
                                    },
                                    "color": {
                                        "type": "string",
                                        "description": "A Tailwind color class for the icon, e.g., 'text-red-500'",
                                    },
                                    "problem": {
                                        "type": "string",
                                        "description": "The title of the problem being addressed, approximately 3-5 words.",
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "A brief explanation of the problem, approximately 20 words.",
                                    },
                                    "impacts": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "A list of potential impacts or consequences of the problem, approximately 3 words each.",
                                    },
                                    "automations": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "A list of potential automations to address the problem, approximately 3-5 words each.",
                                    },
                                },
                                "required": [
                                    "icon",
                                    "color",
                                    "problem",
                                    "description",
                                    "impacts",
                                    "automations",
                                ],
                                "additionalProperties": False,
                            },
                            "description": "Please generate problem cards that match this guidance.",
                        },
                    },
                    "required": ["thinking", "problems"],
                    "additionalProperties": False,
                    "$schema": "http://json-schema.org/draft-07/schema#",
                },
            },
        }
    ]

    optional_params = get_optional_params(
        model="gemini-1.5-flash",
        custom_llm_provider="vertex_ai",
        tools=tools,
    )
    print(optional_params)
    print(optional_params["tools"][0]["function_declarations"][0])
    assert (
        "$schema"
        not in optional_params["tools"][0]["function_declarations"][0]["parameters"]
    )


def test_watsonx_tool_choice():
    optional_params = get_optional_params(
        model="gemini-1.5-pro", custom_llm_provider="watsonx", tool_choice="auto"
    )
    print(optional_params)
    assert optional_params["tool_choice_options"] == "auto"


def test_watsonx_text_top_k():
    optional_params = get_optional_params(
        model="gemini-1.5-pro", custom_llm_provider="watsonx_text", top_k=10
    )
    print(optional_params)
    assert optional_params["top_k"] == 10


def test_together_ai_model_params():
    optional_params = get_optional_params(
        model="together_ai", custom_llm_provider="together_ai", logprobs=1
    )
    print(optional_params)
    assert optional_params["logprobs"] == 1


def test_forward_user_param():
    from litellm.utils import get_supported_openai_params, get_optional_params

    model = "claude-3-5-sonnet-20240620"
    optional_params = get_optional_params(
        model=model,
        user="test_user",
        custom_llm_provider="anthropic",
    )

    assert optional_params["metadata"]["user_id"] == "test_user"


def test_lm_studio_embedding_params():
    optional_params = get_optional_params_embeddings(
        model="lm_studio/gemma2-9b-it",
        custom_llm_provider="lm_studio",
        dimensions=1024,
        drop_params=True,
    )
    assert len(optional_params) == 0


def test_ollama_pydantic_obj():
    from pydantic import BaseModel

    class ResponseFormat(BaseModel):
        x: str
        y: str

    get_optional_params(
        model="qwen2:0.5b",
        custom_llm_provider="ollama",
        response_format=ResponseFormat,
    )


def test_gemini_frequency_penalty():
    from litellm.utils import get_supported_openai_params

    optional_params = get_supported_openai_params(
        model="gemini-1.5-flash",
        custom_llm_provider="vertex_ai",
        request_type="chat_completion",
    )
    assert optional_params is not None
    assert "frequency_penalty" in optional_params
