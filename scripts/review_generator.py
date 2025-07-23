import asyncio
import csv
import logging
import os
import aiohttp
import pandas as pd
from typing import List, Dict, Any

# Добавляем корневую директорию проекта в sys.path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.orchestrator import Orchestrator
from src.core.pdf_extractor import PDFExtractor
from src.core.agents.summary_agent import SummaryAgent
from src.core.agents.structure_agent import StructureAgent

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Константы
DATASET_PATH = 'dataset_100_pdf.csv'
RESULTS_PATH = 'reviews.csv'
TEMP_PDF_DIR = 'temp_pdf'


async def download_pdf(session: aiohttp.ClientSession, url: str, file_path: str) -> bool:
    """Асинхронно скачивает PDF-файл."""
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            with open(file_path, 'wb') as f:
                f.write(await response.read())
            logger.info(f"Successfully downloaded {url} to {file_path}")
            return True
    except aiohttp.ClientError as e:
        logger.error(f"Error downloading {url}: {e}")
        return False


async def process_single_article(session: aiohttp.ClientSession, orchestrator: Orchestrator, pdf_extractor: PDFExtractor, article_id: str, article_url: str) -> Dict[str, Any]:
    """Обрабатывает одну статью: скачивает, извлекает текст и генерирует рецензию."""
    # Используем article_id для создания уникального и валидного имени файла
    safe_article_id = "".join(c for c in article_id if c.isalnum() or c in ('-', '_')).rstrip()
    pdf_filename = os.path.join(TEMP_PDF_DIR, f"{safe_article_id}.pdf")

    # Создаем директорию, если она не существует
    os.makedirs(TEMP_PDF_DIR, exist_ok=True)

    # Скачиваем PDF
    if not await download_pdf(session, article_url, pdf_filename):
        return {"id": article_id, "url": article_url, "review": "Error: Failed to download PDF."}

    try:
        # Извлекаем текст из PDF
        text, metadata = await pdf_extractor.extract(pdf_filename)
        logger.info(f"Extracted text from {pdf_filename}")

        # Обрабатываем текст и генерируем рецензию
        result = await orchestrator.process_paper(text)
        logger.info(f"review generated!")
        review = result.get('final_review', 'Error: Review not generated.')

        return {"id": article_id, "url": article_url, "review": review}

    except Exception as e:
        logger.error(f"Error processing article {article_id}: {e}")
        return {"id": article_id, "url": article_url, "review": f"Error: {e}"}

    finally:
        # Удаляем временный PDF-файл
        if os.path.exists(pdf_filename):
            os.remove(pdf_filename)


async def main():
    """Основная функция для обработки всех статей."""
    # 1. Инициализация
    orchestrator = Orchestrator()
    pdf_extractor = PDFExtractor()
    summary_agent = SummaryAgent(model_name=orchestrator.model_name)
    structure_agent = StructureAgent(model_name=orchestrator.model_name)

    # 2. Регистрация агентов
    orchestrator.register_agent("SummaryAgent", summary_agent)
    orchestrator.register_agent("StructureAgent", structure_agent)

    # 3. Чтение датасета
    try:
        df = pd.read_csv(DATASET_PATH)
        articles = df.to_dict('records')
        logger.info(f"Loaded {len(articles)} articles from {DATASET_PATH}")
        # Ограничиваем количество статей до 20
        # articles = df.head(20).to_dict('records')
        # logger.info(f"Loaded {len(articles)} articles from {DATASET_PATH} (limited to 20)")
    except FileNotFoundError:
        logger.error(f"Dataset file not found: {DATASET_PATH}")
        return
    except Exception as e:
        logger.error(f"Error reading dataset: {e}")
        return

    # 4. Обработка статей
    # Ограничиваем количество одновременных запросов к LLM
    semaphore = asyncio.Semaphore(1)
    results = []

    async def process_article_with_semaphore(session, orchestrator, pdf_extractor, article_id, article_url):
        async with semaphore:
            logger.info(f"Starting processing for article {article_id} with semaphore.")
            result = await process_single_article(session, orchestrator, pdf_extractor, article_id, article_url)
            logger.info(f"Finished processing for article {article_id}.")
            return result

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=900)) as session:
        tasks = []
        for article in articles:
            # В CSV первая колонка - id, вторая - url
            article_id = article[df.columns[0]]
            article_url = article[df.columns[1]]
            tasks.append(process_article_with_semaphore(session, orchestrator, pdf_extractor, article_id, article_url))

        processed_results = await asyncio.gather(*tasks)
        results.extend(processed_results)

    # 5. Сохранение результатов
    if results:
        try:
            with open(RESULTS_PATH, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['id', 'url', 'review']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
            logger.info(f"Successfully saved {len(results)} reviews to {RESULTS_PATH}")
        except IOError as e:
            logger.error(f"Error saving results to CSV: {e}")

if __name__ == "__main__":
    asyncio.run(main())