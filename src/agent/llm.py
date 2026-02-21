from langchain_google_genai import ChatGoogleGenerativeAI

from src.core import logger, settings

LLM = model = ChatGoogleGenerativeAI(
    model=settings.GEMINI_MODEL,
    api_key=settings.GEMINI_API_KEY,
    temperature=1.0,
)


def main() -> None:

    prompt = "Hello there! Can you tell me a joke?"
    try:
        response = LLM.invoke(prompt)
        content = getattr(response, "content", response)
        logger.debug(f"LLM response: {content}")
    except Exception as error:
        logger.exception(f"LLM invocation failed: {error}")
        raise


if __name__ == "__main__":
    main()
