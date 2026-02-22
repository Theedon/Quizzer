import asyncio

from dotenv import load_dotenv

from src.agent.graph import graph_ainvoke
from src.core import configure_logging, logger

load_dotenv()


async def main():
    logger.info("Quizzer started")
    result = await graph_ainvoke()
    logger.info(f"Graph finished with keys: {list(result.keys())}")


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
