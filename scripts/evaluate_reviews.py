import asyncio
import pandas as pd
import ollama
import logging
import re
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
INPUT_CSV_PATH = 'comparable_15.csv'
OUTPUT_CSV_PATH = 'evaluated_reviews.csv'
MODEL_NAME = 'qwen3:4b' # Model for evaluation
CONCURRENT_REQUESTS = 5 # Limit for concurrent requests to the model

EVALUATION_PROMPT_TEMPLATE = """
# Prompt for Evaluating Scientific Article Review Quality

## Task
Compare the test review with the reference review and evaluate the quality of the test version using 5 criteria. The reference review is considered the exemplary version.

## Materials for Evaluation
1. **Reference review**:
{reference_review}

2. **Test review**:
{generated_review}

## Evaluation Criteria (scale 1-5)

### 1. Logical Consistency
**What to evaluate:** The coherence of presentation and consistency of argumentation compared to the reference.

**How to score:**
- **5** — Clear logic like in the reference: each comment follows from analysis, conclusions are justified
- **4** — Mostly logical, but 1-2 statements lack sufficient justification
- **3** — Some logical inconsistencies (example: criticizes methodology but praises results obtained by it)
- **2** — Multiple contradictions between different parts of the review
- **1** — Chaotic presentation with no connection between comments and conclusions

### 2. Coverage of Strengths
**What to evaluate:** Presence and quality of describing the article's strong points compared to the reference.

**How to score:**
- **5** — All key strengths from the reference are noted with explanation of their importance
- **4** — Most strengths mentioned, but 1-2 minor ones missed
- **3** — Main strengths noted but without detail, or important points missed
- **2** — Strengths mentioned only formally or only a small portion from the reference
- **1** — No strengths mentioned or reduced to generic phrases like "interesting topic"

### 3. Identification of Problems and Weaknesses
**What to evaluate:** Completeness and specificity of critical comments compared to the reference.

**How to score:**
- **5** — All significant problems from the reference are identified and specifically described with examples
- **4** — Main weaknesses indicated in detail, only minor points missed
- **3** — Key problems named but some lack specifics, or 1-2 important comments missed
- **2** — Only some problems indicated, many comments are vague
- **1** — Criticism is superficial or absent, problems don't match the reference

### 4. Practical Usefulness of Recommendations
**What to evaluate:** Presence and quality of specific suggestions for improving the work compared to the reference.

**How to score:**
- **5** — All important recommendations from the reference given, each is clear and actionable (example: "add statistical hypothesis testing")
- **4** — 1 minor recommendation missed, others are specific and useful
- **3** — 1-2 important recommendations from reference missing or some advice too general
- **2** — Only basic recommendations given, key improvement suggestions missed
- **1** — Recommendations absent or presented as general phrases without practical value

### 5. Scientific Style and Professionalism
**What to evaluate:** Correspondence of language, tone, and format to the academic standards of the reference.

**How to score:**
- **5** — Impeccable scientific style: correct terminology, objective tone, structured presentation, respectful attitude
- **4** — Professional style with minimal deviations (1-2 imprecise terms or colloquial expressions)
- **3** — Generally scientific style, but some emotional assessments or simplified vocabulary present
- **2** — Notable problems: many colloquial expressions, subjective judgments, breach of academic ethics
- **1** — Unacceptable style: rudeness, dismissiveness, everyday language, or personal attacks

## Response Format
```
Criterion 1: [score] — [justification in 1-2 sentences]
Criterion 2: [score] — [justification in 1-2 sentences]
Criterion 3: [score] — [justification in 1-2 sentences]
Criterion 4: [score] — [justification in 1-2 sentences]
Criterion 5: [score] — [justification in 1-2 sentences]

Total score: [sum of scores]/25
```
"""

async def evaluate_review(semaphore: asyncio.Semaphore, reference_review: str, generated_review: str, row_index: int) -> Dict[str, Any]:
    """Sends a request to the model to evaluate a review, controlling concurrency with a semaphore."""
    async with semaphore:
        logger.info(f"Starting evaluation for row {row_index}")
        prompt = EVALUATION_PROMPT_TEMPLATE.format(
            reference_review=reference_review,
            generated_review=generated_review
        )
        try:
            response = await asyncio.to_thread(
                ollama.chat,
                model=MODEL_NAME,
                messages=[{'role': 'user', 'content': prompt}]
            )
            logger.info(f"Finished evaluation for row {row_index}")
            return parse_evaluation(response['message']['content'])
        except Exception as e:
            logger.error(f"Error during evaluation for row {row_index}: {e}")
            return {"error": str(e), "raw_response": ""}

def parse_evaluation(text: str) -> Dict[str, Any]:
    """Parses the model's response and extracts scores, processing the text line by line."""
    parsed_data = {
        f'criterion_{i}_score': 0 for i in range(1, 6)
    }
    parsed_data.update({
        f'criterion_{i}_justification': '' for i in range(1, 6)
    })
    parsed_data.update({
        'total_score': 0,
        'parsing_error': None,
        'raw_response': text
    })

    try:
        lines = text.strip().split('\n')
        
        # Pattern for finding criteria
        crit_pattern = re.compile(r"Criterion\s+(\d):\s*(\d+)\s*[-—]?\s*(.*)", re.IGNORECASE)
        
        found_scores = {}

        for line in lines:
            match = crit_pattern.match(line.strip())
            if match:
                crit_num = int(match.group(1))
                score = int(match.group(2))
                justification = match.group(3).strip()
                
                if 1 <= crit_num <= 5:
                    found_scores[crit_num] = score
                    parsed_data[f'criterion_{crit_num}_score'] = score
                    parsed_data[f'criterion_{crit_num}_justification'] = justification

        # Calculate total score as the sum of found scores
        calculated_score = sum(found_scores.values())
        parsed_data['total_score'] = calculated_score
        
        # Look for the total score specified by the model and use it if found
        total_score_match = re.search(r"Total score:\s*(\d+)", text, re.IGNORECASE)
        if total_score_match:
            parsed_data['total_score'] = int(total_score_match.group(1))

        found_criteria_count = len(found_scores)
        if found_criteria_count < 5:
             logger.warning(f"Parser found only {found_criteria_count}/5 criteria in response.")

    except Exception as e:
        logger.error(f"Error parsing evaluation response: '{text}'. Error: {e}")
        parsed_data['parsing_error'] = str(e)

    return parsed_data

async def main():
    """Main function for evaluating reviews."""
    try:
        df = pd.read_csv(INPUT_CSV_PATH)
        logger.info(f"Loaded {len(df)} records from {INPUT_CSV_PATH}")
    except FileNotFoundError:
        logger.error(f"Input file not found: {INPUT_CSV_PATH}")
        return

    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    tasks = []
    for index, row in df.iterrows():
        tasks.append(
            evaluate_review(
                semaphore,
                row['reviews_full_text'],
                row['generated_review'],
                index + 1
            )
        )
    
    evaluations = await asyncio.gather(*tasks)

    results = []
    for (index, row), evaluation in zip(df.iterrows(), evaluations):
        result_row = row.to_dict()
        result_row.update(evaluation)
        results.append(result_row)

    output_df = pd.DataFrame(results)
    
    # Reorder columns to have evaluation results at the end
    original_columns = df.columns.tolist()
    new_columns = [col for col in output_df.columns if col not in original_columns]
    final_columns = original_columns + sorted(new_columns) # Sort new columns for consistency
    output_df = output_df[final_columns]
    
    try:
        output_df.to_csv(OUTPUT_CSV_PATH, index=False)
        logger.info(f"Successfully saved {len(output_df)} evaluated reviews to {OUTPUT_CSV_PATH}")
    except IOError as e:
        logger.error(f"Error saving results to CSV: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 