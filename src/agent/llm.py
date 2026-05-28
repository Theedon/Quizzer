from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from ..core import logger, settings


def get_llm(
    provider: str | None = None,
    model: str | None = None,
) -> BaseChatModel:
    """Build the LLM client for the active (or given) provider.

    When *provider* or *model* are supplied they take precedence over the
    global ``settings`` values.  This allows callers (e.g. per-session UI
    state) to choose a provider/model without mutating the shared singleton.
    """
    chosen = provider or settings.MODEL_PROVIDER

    if chosen == "google":
        return ChatGoogleGenerativeAI(
            model=model or settings.GEMINI_MODEL,
            api_key=SecretStr(settings.GEMINI_API_KEY),
            temperature=1.0,
        )
    if chosen == "groq":
        return ChatGroq(
            model=model or settings.GROQ_MODEL,
            api_key=SecretStr(settings.GROQ_API_KEY),
            temperature=1.0,
        )
    if chosen == "openai":
        return ChatOpenAI(
            model=model or settings.OPENAI_MODEL,
            api_key=SecretStr(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None,
        )
    raise ValueError(f"Unsupported model provider: {chosen}")


def main() -> None:

    prompt = "Hello there! Can you tell me a joke?"
    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        logger.debug(f"LLM response: {content}")
    except Exception as error:
        logger.exception(f"LLM invocation failed: {error}")
        raise


if __name__ == "__main__":
    main()
