import asyncio

from dotenv import load_dotenv

from .agent.graph import graph_ainvoke
from .core import configure_logging, logger
from .utils.export import export_quizzes_to_csv

load_dotenv()


async def main():
    logger.info("Quizzer started")
    result = await graph_ainvoke(pdf_url_or_base64=pdf_input)
    logger.info(f"Graph finished with keys: {list(result.keys())}")

    final_quiz_data = result.get("final_quiz", [])
    filepath = export_quizzes_to_csv(final_quiz_data, custom_filepath=csv_output)


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
