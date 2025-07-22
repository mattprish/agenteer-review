import fitz  # PyMuPDF
import logging
import tempfile
import os
from typing import Dict, Any, Tuple, List, Optional
import aiofiles
from pathlib import Path
import re

logger = logging.getLogger(__name__)

class PDFExtractor:
    """Класс для извлечения текста из PDF файлов с улучшенной обработкой"""
    
    def __init__(self):
        self.supported_extensions = ['.pdf']
        logger.info("PDFExtractor initialized")
    
    async def extract(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Извлекает текст и метаданные из PDF файла
        
        Args:
            file_path: Путь к PDF файлу
            
        Returns:
            Tuple[str, Dict]: (извлеченный_текст, метаданные)
        """
        logger.info(f"Starting PDF extraction from: {file_path}")
        
        try:
            # Открываем PDF документ
            doc = fitz.open(file_path)
            
            # Извлекаем метаданные
            metadata = self._extract_metadata(doc)
            
            # Извлекаем текст с улучшенной обработкой
            text = self._extract_text_enhanced(doc)
            
            # Закрываем документ
            doc.close()
            
            logger.info(f"Successfully extracted {len(text)} characters from PDF")
            
            return text, metadata
            
        except Exception as e:
            logger.error(f"Error extracting PDF: {e}")
            raise Exception(f"Failed to extract PDF: {str(e)}")
    
    async def extract_from_bytes(self, pdf_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
        """
        Извлекает текст и метаданные из PDF файла в виде байтов
        
        Args:
            pdf_bytes: PDF файл в виде байтов
            
        Returns:
            Tuple[str, Dict]: (извлеченный_текст, метаданные)
        """
        logger.info("Starting PDF extraction from bytes")
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(pdf_bytes)
            temp_path = temp_file.name
        
        try:
            # Извлекаем текст из временного файла
            text, metadata = await self.extract(temp_path)
            return text, metadata
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def _extract_metadata(self, doc: fitz.Document) -> Dict[str, Any]:
        """Извлекает метаданные из PDF документа"""
        metadata = {
            "page_count": len(doc),
            "title": "",
            "author": "",
            "subject": "",
            "creator": "",
            "producer": "",
            "creation_date": "",
            "modification_date": "",
            "has_text": False,
            "has_images": False,
            "has_tables": False,
            "pages_with_text": 0,
            "pages_with_images": 0,
            "total_words": 0
        }
        
        try:
            # Получаем метаданные документа
            doc_metadata = doc.metadata
            
            if doc_metadata:
                metadata.update({
                    "title": doc_metadata.get("title", ""),
                    "author": doc_metadata.get("author", ""),
                    "subject": doc_metadata.get("subject", ""),
                    "creator": doc_metadata.get("creator", ""),
                    "producer": doc_metadata.get("producer", ""),
                    "creation_date": doc_metadata.get("creationDate", ""),
                    "modification_date": doc_metadata.get("modDate", "")
                })
            
            # Анализируем содержимое страниц
            pages_with_text = 0
            pages_with_images = 0
            total_words = 0
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Проверяем наличие текста
                text = page.get_text().strip()
                if text:
                    pages_with_text += 1
                    total_words += len(text.split())
                
                # Проверяем наличие изображений
                image_list = page.get_images()
                if image_list:
                    pages_with_images += 1
            
            metadata.update({
                "has_text": pages_with_text > 0,
                "has_images": pages_with_images > 0,
                "pages_with_text": pages_with_text,
                "pages_with_images": pages_with_images,
                "total_words": total_words
            })
            
            logger.info(f"Extracted metadata: {metadata['page_count']} pages, {pages_with_text} with text, {pages_with_images} with images")
            
        except Exception as e:
            logger.warning(f"Could not extract metadata: {e}")
        
        return metadata
    
    def _extract_text_enhanced(self, doc: fitz.Document) -> str:
        """Улучшенное извлечение текста с сохранением структуры"""
        all_content = []
        
        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                page_content = []
                
                # Добавляем заголовок страницы
                page_content.append(f"\n{'='*50}")
                page_content.append(f"СТРАНИЦА {page_num + 1}")
                page_content.append(f"{'='*50}\n")
                
                # Извлекаем текст с блоками для сохранения структуры
                text_blocks = self._extract_text_blocks(page)
                
                if text_blocks:
                    page_content.extend(text_blocks)
                else:
                    # Если нет блоков, пробуем обычное извлечение
                    simple_text = page.get_text()
                    if simple_text.strip():
                        page_content.append(simple_text)
                    else:
                        page_content.append("[Страница не содержит текста]")
                
                # Извлекаем информацию о таблицах и изображениях
                table_info = self._extract_table_info(page)
                if table_info:
                    page_content.append("\n[ТАБЛИЦЫ НА СТРАНИЦЕ]")
                    page_content.extend(table_info)
                
                image_info = self._extract_image_info(page)
                if image_info:
                    page_content.append("\n[ИЗОБРАЖЕНИЯ НА СТРАНИЦЕ]")
                    page_content.extend(image_info)
                
                all_content.extend(page_content)
                
            except Exception as e:
                logger.warning(f"Could not extract content from page {page_num + 1}: {e}")
                all_content.append(f"\n[ОШИБКА НА СТРАНИЦЕ {page_num + 1}: {str(e)}]\n")
                continue
        
        combined_text = "\n".join(all_content)
        
        # Улучшенная очистка текста
        cleaned_text = self._clean_text_enhanced(combined_text)
        
        return cleaned_text
    
    def _extract_text_blocks(self, page: fitz.Page) -> List[str]:
        """Извлекает текстовые блоки с сохранением структуры"""
        blocks = []
        
        try:
            # Получаем текстовые блоки
            text_dict = page.get_text("dict")
            
            for block in text_dict["blocks"]:
                if "lines" in block:  # Текстовый блок
                    block_text = []
                    
                    for line in block["lines"]:
                        line_text = ""
                        for span in line["spans"]:
                            line_text += span["text"]
                        
                        if line_text.strip():
                            block_text.append(line_text.strip())
                    
                    if block_text:
                        blocks.append("\n".join(block_text))
        
        except Exception as e:
            logger.warning(f"Could not extract text blocks: {e}")
            # Фолбэк к простому извлечению
            simple_text = page.get_text()
            if simple_text.strip():
                blocks.append(simple_text)
        
        return blocks
    
    def _extract_table_info(self, page: fitz.Page) -> List[str]:
        """Извлекает информацию о таблицах на странице"""
        table_info = []
        
        try:
            # Ищем табличные структуры
            tables = page.find_tables()
            
            for i, table in enumerate(tables):
                table_info.append(f"Таблица {i+1}:")
                
                # Извлекаем содержимое таблицы
                try:
                    table_data = table.extract()
                    for row_idx, row in enumerate(table_data):
                        if row and any(cell and str(cell).strip() for cell in row):
                            row_text = " | ".join(str(cell).strip() if cell else "" for cell in row)
                            table_info.append(f"  Строка {row_idx+1}: {row_text}")
                except Exception as e:
                    table_info.append(f"  [Ошибка извлечения данных таблицы: {e}]")
                
                table_info.append("")  # Пустая строка после таблицы
        
        except Exception as e:
            logger.debug(f"Could not extract table info: {e}")
        
        return table_info
    
    def _extract_image_info(self, page: fitz.Page) -> List[str]:
        """Извлекает информацию об изображениях на странице"""
        image_info = []
        
        try:
            image_list = page.get_images()
            
            for i, img in enumerate(image_list):
                try:
                    # Получаем информацию об изображении
                    xref = img[0]
                    base_image = page.parent.extract_image(xref)
                    
                    image_data = {
                        "index": i + 1,
                        "width": base_image.get("width", "неизвестно"),
                        "height": base_image.get("height", "неизвестно"),
                        "colorspace": base_image.get("colorspace", "неизвестно"),
                        "size": len(base_image.get("image", b""))
                    }
                    
                    info_text = (f"Изображение {image_data['index']}: "
                               f"{image_data['width']}x{image_data['height']} пикселей, "
                               f"размер: {image_data['size']} байт")
                    
                    image_info.append(info_text)
                    
                except Exception as e:
                    image_info.append(f"Изображение {i+1}: [Ошибка получения информации: {e}]")
        
        except Exception as e:
            logger.debug(f"Could not extract image info: {e}")
        
        return image_info
    
    def _clean_text_enhanced(self, text: str) -> str:
        """Улучшенная очистка извлеченного текста"""
        # Нормализуем переносы строк
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\r', '\n', text)
        
        # Убираем лишние пробелы, но сохраняем структуру
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Убираем лишние переносы строк (более 2 подряд)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Убираем пробелы в начале строк, кроме намеренных отступов
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Сохраняем строки с разделителями и заголовками
            if line.strip().startswith('=') or line.strip().startswith('[') or line.strip().startswith('СТРАНИЦА'):
                cleaned_lines.append(line.strip())
            else:
                # Убираем только лишние пробелы в начале
                cleaned_lines.append(line.strip())
        
        text = '\n'.join(cleaned_lines)
        
        # Убираем пробелы в начале и конце всего текста
        text = text.strip()
        
        return text
    
    def validate_file_size(self, file_size: int, max_size: int = 10 * 1024 * 1024) -> bool:
        """Проверяет размер файла"""
        return file_size <= max_size
    
    def validate_file_extension(self, filename: str) -> bool:
        """Проверяет расширение файла"""
        return Path(filename).suffix.lower() in self.supported_extensions 