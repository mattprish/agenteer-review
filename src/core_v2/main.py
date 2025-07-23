from agentlib.orchestrator import Orchestrator
from agentlib.base_agent import BaseAgent
import argparse
from pdf.pdf import pdf_url_to_text

def main():
    agents_prompts = {
        "AbstractAgent": """
            Analyze the abstract and introduction of the provided scientific paper. Assess the clarity of the research question, the novelty of the work, and the significance of the stated contributions. Provide a score from 0 to 10 for each of these three aspects (Clarity, Novelty, Significance), where 0 is poor, 4-7 is average, and 8-10 is excellent. Summarize your findings in a short paragraph.
        """,
        "MethodologyAgent":"""
            Examine the methodology section of the paper. Evaluate the clarity and completeness of the described methods. Assess whether the experimental setup is sound and if the work appears to be reproducible based on the information provided. Provide a score from 0 to 10 for both Clarity of Methods and Reproducibility, where 0 is poor, 4-7 is average, and 8-10 is excellent. List any identified flaws or areas needing further clarification.
        """,
        "ResultsAgent":"""
            Analyze the results and discussion sections. Assess whether the presented results are clearly explained and logically support the paper's main claims. Evaluate the quality of the discussion in interpreting the results and contextualizing them within the broader field. Provide a score from 0 to 10 for both Clarity of Results and Quality of Discussion, where 0 is poor, 4-7 is average, and 8-10 is excellent. Highlight any inconsistencies or unsupported claims.
        """,
        "LanguageAgent":"""
            Perform a thorough check of the entire paper for grammatical errors, spelling mistakes, and awkward phrasing. Identify sentences or paragraphs that are unclear due to poor language. Provide a score from 0 to 10 for the overall linguistic quality of the paper, where 0 is poor, 4-7 is average, and 8-10 is excellent. List the most significant grammatical issues found.
        """,
        "CitationAgent":"""
            Verify the formatting and consistency of the citations and reference list. Check for any obvious errors in the references, such as missing information or incorrect formatting. Assess whether the references are relevant and up-to-date. Provide a score from 0 to 10 for the quality of citations and referencing, where 0 is poor, 4-7 is average, and 8-10 is excellent.
        """
    }
    parser = argparse.ArgumentParser(description = "Link to the paper")
    parser.add_argument("url",help = "Input URL")
    args = parser.parse_args()
    url =  args.url.replace("forum", "pdf")
    paper = pdf_url_to_text(url)
    model_url = "https://8d586b648815.ngrok-free.app/v1"
    model_name = "qwen/qwen3-4b"
    agents = [
        BaseAgent("AbstractAgent",model_url,model_name,agents_prompts["AbstractAgent"]),
        BaseAgent("MethodologyAgent",model_url,model_name,agents_prompts["MethodologyAgent"]),
        BaseAgent("ResultsAgent",model_url,model_name,agents_prompts["ResultsAgent"]),
        BaseAgent("LanguageAgent",model_url,model_name,agents_prompts["LanguageAgent"]),
        BaseAgent("CitationAgent",model_url,model_name,agents_prompts["CitationAgent"]),
    ]
    orchestrator = Orchestrator(
        model_url,
        model_name,
        agents
    )
    result = orchestrator.run(paper)
    print(result)

if __name__ == "__main__":
    main()
