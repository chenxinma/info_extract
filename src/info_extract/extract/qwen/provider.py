"""Minimal dummy of a qwen provider plugin for LangExtract."""
from __future__ import annotations

import dataclasses
from typing import Any, Iterator, Sequence

from . import schema as custom_schema

import langextract as lx
from langextract.core.schema import BaseSchema
from langextract.core.base_model import BaseLanguageModel

@lx.providers.registry.register(
    r'^qwen',  # Matches Gemini model IDs (same as default provider)
    r'^deepseek',
)
@dataclasses.dataclass(init=False)
class QwenProvider(BaseLanguageModel):
    model_id: str
    api_key: str | None
    base_url: str
    temperature: float
    response_schema: dict[str, Any] | None = None
    enable_structured_output: bool = False
    _client: Any = dataclasses.field(repr=False, compare=False)

    def __init__(
        self,
        model_id: str = 'qwen3-coder-flash',
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> None:
        """Initialize the custom provider.

        Args:
        model_id: The model ID.
        api_key: API key for the service.
        temperature: Sampling temperature.
        **kwargs: Additional parameters.
        """
        super().__init__()

        try:
            from openai import OpenAI  # pylint: disable=import-outside-toplevel
        except ImportError as e:
            raise lx.exceptions.InferenceConfigError(
                'This example requires openai package. '
                'Install with: pip install openai'
            ) from e

        self.model_id = model_id
        self.api_key = api_key
        self.base_url = base_url or 'https://dashscope.aliyuncs.com/compatible-mode/v1'
        self.temperature = temperature

        # Schema kwargs from CustomProviderSchema.to_provider_config()
        self.response_schema = kwargs.get('response_schema')
        self.enable_structured_output = kwargs.get(
            'enable_structured_output', False
        )

        # Store any additional kwargs for potential use
        self._extra_kwargs = kwargs

        if not self.api_key:
            raise lx.exceptions.InferenceConfigError(
                'API key required. Set GEMINI_API_KEY or pass api_key parameter.'
            )

        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    @classmethod
    def get_schema_class(cls) -> type[BaseSchema] | None:
        """Return our custom schema class.

        This allows LangExtract to use our custom schema implementation
        when use_schema_constraints=True is specified.

        Returns:
        Our custom schema class that will be used to generate constraints.
        """
        return custom_schema.QwenProviderSchema

    def apply_schema(self, schema_instance: BaseSchema | None) -> None:
        """Apply or clear schema configuration.

        This method is called by LangExtract to dynamically apply schema
        constraints after the provider is instantiated. It's important to
        handle both the application of a new schema and clearing (None).

        Args:
        schema_instance: The schema to apply, or None to clear existing schema.
        """
        super().apply_schema(schema_instance)

        if schema_instance:
            # Apply the new schema configuration
            config = schema_instance.to_provider_config()
            self.response_schema = config.get('response_schema')
            self.enable_structured_output = config.get(
                'enable_structured_output', False
            )
        else:
            # Clear the schema configuration
            self.response_schema = None
            self.enable_structured_output = False

    def infer(
        self, batch_prompts: Sequence[str], **kwargs: Any
    ) -> Iterator[Sequence[lx.core.types.ScoredOutput]]:
        """Run inference on a batch of prompts.

        Args:
        batch_prompts: Input prompts to process.
        **kwargs: Additional generation parameters.

        Yields:
        Lists of ScoredOutputs, one per prompt.
        """
        config = {
            'temperature': kwargs.get('temperature', self.temperature),
        }

        # Add other parameters if provided
        for key in ['max_output_tokens', 'top_p', 'top_k']:
            if key in kwargs:
                config[key] = kwargs[key]

        # Apply schema constraints if configured
        if self.response_schema and self.enable_structured_output:
            # For Gemini, this ensures the model outputs JSON matching our schema
            # Adapt this section based on your actual provider's API requirements
            config['response_schema'] = self.response_schema
            config['response_mime_type'] = 'application/json'

        for prompt in batch_prompts:
            try:
                response = self._client.chat.completions.create(
                    model=self.model_id,
                    messages=[{"role": "user", "content": prompt}, ]
                )
                output = response.choices[0].message.content.strip()
                yield [lx.core.types.ScoredOutput(score=1.0, output=output)]

            except Exception as e:
                raise lx.exceptions.InferenceRuntimeError(
                    f'API error: {str(e)}', original=e
                ) from e
