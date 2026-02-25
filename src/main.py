import argparse
import asyncio

from dotenv import load_dotenv
from langgraph.types import StateSnapshot

from .agent.graph import graph_ainvoke
from .core import configure_logging, logger
from .utils.export import export_quizzes_to_csv

load_dotenv()


async def main(pdf_input: str, csv_output: str | None = None) -> str | None:
    logger.info("Quizzer started")
    result = await graph_ainvoke(pdf_url_or_base64=pdf_input)
    state_values = result.values if isinstance(result, StateSnapshot) else result
    logger.info(f"Graph finished with keys: {list(state_values.keys())}")

    final_quiz_data = state_values.get("final_quiz", [])
    filepath = export_quizzes_to_csv(final_quiz_data, custom_filepath=csv_output)

    return filepath


def cli():
    parser = argparse.ArgumentParser(
        description="Quizzer: AI Map-Reduce Quiz Generator"
    )
    parser.add_argument(
        "--input", type=str, required=True, help="Path to the input PDF"
    )
    parser.add_argument(
        "--output", type=str, help="Optional custom path for the output CSV"
    )

    args = parser.parse_args()
    configure_logging()
    asyncio.run(main(args.input, args.output))


if __name__ == "__main__":
    cli()
