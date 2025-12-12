import logging
import os
from enum import Enum


class LLMType(Enum):
    """Supported LLM types"""

    # Paid API-based models
    OPENAI_GPT4 = "openai_gpt4"
    OPENAI_GPT35 = "openai_gpt35"
    ANTHROPIC_CLAUDE = "anthropic_claude"

    # Free HuggingFace models (run locally)
    HUGGINGFACE_FLAN_T5 = "huggingface_flan_t5"
    HUGGINGFACE_GPT2 = "huggingface_gpt2"
    HUGGINGFACE_DIALOGPT = "huggingface_dialogpt"

    # Ollama (free local models)
    OLLAMA = "ollama"


class LLMService:
    """
    Service for calling various LLM providers.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_handlers = {
            LLMType.OPENAI_GPT4: lambda llm_type, prompt: self._call_openai(
                llm_type, prompt
            ),
            LLMType.OPENAI_GPT35: lambda llm_type, prompt: self._call_openai(
                llm_type, prompt
            ),
            LLMType.ANTHROPIC_CLAUDE: lambda llm_type, prompt: self._call_anthrpc(
                prompt
            ),
            LLMType.HUGGINGFACE_FLAN_T5: lambda llm_type, prompt: self._call_hgf(
                "google/flan-t5-base", prompt
            ),
            LLMType.HUGGINGFACE_GPT2: lambda llm_type, prompt: self._call_hgf(
                "gpt2", prompt
            ),
            LLMType.HUGGINGFACE_DIALOGPT: lambda llm_type, prompt: self._call_hgf(
                "microsoft/DialoGPT-medium", prompt
            ),
            LLMType.OLLAMA: lambda llm_type, prompt: self._call_ollama(prompt),
        }

    def call_llm(self, llm_type: LLMType, prompt: str) -> str:
        """
        Call an LLM with the given prompt.

        Args:
            llm_type: The type of LLM to use (LLMType enum)
            prompt: The prompt to send to the LLM

        Returns:
            The LLM's response as a string

        Raises:
            ValueError: If the LLM type is not supported or API key is missing
            Exception: If the API call fails
        """
        self.logger.info(f"Calling {llm_type.value} with prompt length: {len(prompt)}")

        handler = self.llm_handlers.get(llm_type)

        if handler:
            return handler(llm_type, prompt)
        else:
            raise ValueError(f"Unsupported LLM type: {llm_type}")

    def _call_openai(self, llm_type: LLMType, prompt: str) -> str:
        """Call OpenAI API"""
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package is required. Install it with: pip install openai"
            )

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please set it to your OpenAI API key."
            )

        openai.api_key = api_key

        model = "gpt-4" if llm_type == LLMType.OPENAI_GPT4 else "gpt-3.5-turbo"

        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"OpenAI API call failed: {e}")
            raise

    def _call_anthrpc(self, prompt: str) -> str:
        """Call Anthropic Claude API"""
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package is required. Install it with: pip install anthropic"
            )

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please set it to your Anthropic API key."
            )

        client = anthropic.Anthropic(api_key=api_key)

        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            self.logger.error(f"Anthropic API call failed: {e}")
            raise

    def _call_hgf(self, model_id: str, prompt: str) -> str:
        """
        Call HuggingFace models using langchain.

        Args:
            model_id: HuggingFace model ID (e.g., "google/flan-t5-base")
            prompt: The prompt to send to the model

        Returns:
            The model's response
        """
        try:
            from langchain_huggingface import HuggingFacePipeline
        except ImportError:
            raise ImportError(
                "langchain-huggingface package is required. "
                "Install it with: pip install langchain-huggingface"
            )

        self.logger.info(f"Loading HuggingFace model: {model_id}")

        try:
            pipeline_kwargs = {
                "max_new_tokens": 512,
                "temperature": 0.7,
            }

            # TODO SST: Remove the whole model
            # Add pad_token_id for DialoGPT
            if "DialoGPT" in model_id or "gpt2" in model_id:
                pipeline_kwargs["pad_token_id"] = 50256

            # Create the HuggingFace pipeline
            hf = HuggingFacePipeline.from_model_id(
                model_id=model_id,
                task=(
                    "text-generation"
                    if "gpt" in model_id.lower()
                    else "text2text-generation"
                ),
                pipeline_kwargs=pipeline_kwargs,
            )

            response = hf.invoke(prompt)

            self.logger.info(f"HuggingFace model response length: {len(response)}")
            return response

        except Exception as e:
            self.logger.error(f"HuggingFace model call failed: {e}")
            raise

    def _call_ollama(self, prompt: str, model: str = "llama2") -> str:
        """
        Call Ollama for local LLM inference.

        Args:
            prompt: The prompt to send to the model
            model: Ollama model name (default: llama2)

        Returns:
            The model's response

        Note:
            Requires Ollama to be installed and running locally.
            Install from: https://ollama.ai
        """
        try:
            from langchain_community.llms import Ollama
        except ImportError:
            raise ImportError(
                "langchain-community package is required. "
                "Install it with: pip install langchain-community"
            )

        # Allow model override via environment variable
        model = os.getenv("OLLAMA_MODEL", model)

        self.logger.info(f"Calling Ollama with model: {model}")

        try:
            llm = Ollama(model=model)
            response = llm.invoke(prompt)
            return response
        except Exception as e:
            self.logger.error(
                f"Ollama call failed: {e}. "
                "Make sure Ollama is installed and running (https://ollama.ai)"
            )
            raise
