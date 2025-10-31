import os
from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

load_dotenv()
_model_id = os.environ.get("SPREAD_MODEL_ID")
_api_key = os.environ.get("SPREAD_API_KEY")
_base_url = os.environ.get("SPREAD_BASE_URL")

def qwen():
    _provider = OpenAIProvider(base_url=_base_url, api_key=_api_key)
    _model = OpenAIChatModel(model_name=str(_model_id), provider=_provider)
    return _model