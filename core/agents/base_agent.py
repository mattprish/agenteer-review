from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Базовый класс для всех агентов"""
    
    def __init__(self, name: str):
        self.name = name
        logger.info(f"Initializing agent: {self.name}")
    
    @abstractmethod
    async def analyze(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует текст и возвращает результаты"""
        pass
    
    @abstractmethod
    def get_prompt_template(self) -> str:
        """Возвращает шаблон промпта для оркестратора"""
        pass
    
    def get_name(self) -> str:
        """Возвращает имя агента"""
        return self.name 