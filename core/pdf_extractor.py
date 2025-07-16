import fitz  # PyMuPDF
import logging
import tempfile
import os
from typing import Dict, Any, Tuple
import aiofiles
from pathlib import Path

logger = logging.getLogger(__name__)

class PDFExtractor:
    """Класс для извлечения текста из PDF файлов"""
    
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
            
            # Извлекаем текст
            text = self._extract_text(doc)
            
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
            "modification_date": ""
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
            
            logger.info(f"Extracted metadata: {metadata['page_count']} pages")
            
        except Exception as e:
            logger.warning(f"Could not extract metadata: {e}")
        
        return metadata
    
    def _extract_text(self, doc: fitz.Document) -> str:
        """Извлекает текст из всех страниц PDF документа"""
        all_text = []
        
        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                
                # Извлекаем текст со страницы
                page_text = page.get_text()
                
                if page_text.strip():
                    all_text.append(f"--- Страница {page_num + 1} ---\n")
                    all_text.append(page_text)
                    all_text.append("\n")
                
            except Exception as e:
                logger.warning(f"Could not extract text from page {page_num + 1}: {e}")
                continue
        
        combined_text = "".join(all_text)
        
        # Очищаем текст
        cleaned_text = self._clean_text(combined_text)
        
        return cleaned_text
    
    def _clean_text(self, text: str) -> str:
        """Очищает извлеченный текст"""
        # Убираем лишние пробелы и переносы строк
        import re
        
        # Убираем лишние пробелы
        text = re.sub(r'\s+', ' ', text)
        
        # Убираем лишние переносы строк
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Убираем пробелы в начале и конце
        text = text.strip()
        
        return text
    
    def validate_file_size(self, file_size: int, max_size: int = 10 * 1024 * 1024) -> bool:
        """Проверяет размер файла"""
        return file_size <= max_size
    
    def validate_file_extension(self, filename: str) -> bool:
        """Проверяет расширение файла"""
        return Path(filename).suffix.lower() in self.supported_extensions 