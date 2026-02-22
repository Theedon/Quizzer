from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from pydantic import SecretStr

from src.core import logger, settings

GoogleLLM = ChatGoogleGenerativeAI(
    model=settings.GEMINI_MODEL,
    api_key=SecretStr(settings.GEMINI_API_KEY),
    temperature=1.0,
)

GroqLLM = ChatGroq(
    model=settings.GROQ_MODEL,
    api_key=SecretStr(settings.GROQ_API_KEY),
    temperature=1.0,
)


def get_llm(provider: str = settings.MODEL_PROVIDER):
    if provider == "google":
        return GoogleLLM
    elif provider == "groq":
        return GroqLLM
    else:
        raise ValueError(f"Unsupported model provider: {provider}")


LLM = MODEL = get_llm()


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
