import asyncio
from src.core.orchestrator import Orchestrator, IterativeOrchestrator
from src.core.base_agent import BaseAgent
from src.core.prompts import agents_prompts
import argparse
from src.core.pdf.pdf import pdf_url_to_text

model_url = "https://.../v1"  # url to model


async def main():
    # parser = argparse.ArgumentParser(description="Link to the paper")
    # parser.add_argument("url", help="Input URL")
    # args = parser.parse_args()
    # url = args.url.replace("forum", "pdf")
    # paper = pdf_url_to_text(url)
    paper = """
    COUNTEREXAMPLE TO EULER'S CONJECTURE ON SUMS OF LIKE POWERS BY L. J. LANDER AND T. R. PARKIN
    Communicated by J. D. Swift, June 27, 1966
    A direct search on the CDC 6600 yielded
    275 + 845+1105 +1335 = 1445
    as the smallest instance in which four fifth powers sum to a fifth power. This is a counterexample to a conjecture by Euler [1] that at least n nth powers are required to sum to an nth power, n > 2.
    REFERENCE
    1. L. E. Dickson, History of the theory of numbers, Vol. 2, Chelsea, New York,
    1952, p. 648.
    """

    model_name = "qwen/qwen3-4b"
    agents = [
        BaseAgent("AbstractAgent", model_url, model_name, agents_prompts["AbstractAgent"]),
        # BaseAgent("SummaryAgent", model_url, model_name, agents_prompts["SummaryAgent"]),
        # BaseAgent("StrengthAgent", model_url, model_name, agents_prompts["StrengthAgent"]),
        # BaseAgent("WeaknessesAgent", model_url, model_name, agents_prompts["WeaknessesAgent"]),
        # BaseAgent("QuestionAgent", model_url, model_name, agents_prompts["QuestionAgent"]),
    ]
    # orchestrator = Orchestrator(
    #     model_url,
    #     model_name,
    #     agents,
    # )

    orchestrator = IterativeOrchestrator(
        model_url,
        model_name,
        agents,
    )
    result = await orchestrator.run(paper)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
