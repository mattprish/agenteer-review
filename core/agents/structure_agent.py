import re
import logging
from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class StructureAgent(BaseAgent):
    """Агент для анализа структуры научной статьи"""
    
    def __init__(self):
        super().__init__("StructureAgent")
        self.expected_sections = [
            "abstract", "introduction", "methodology", "method",
            "results", "discussion", "conclusion", "references"
        ]
        
        # Паттерны для определения секций
        self.section_patterns = {
            "abstract": [
                r"\babstract\b",
                r"\bаннотация\b",
                r"\bрезюме\b"
            ],
            "introduction": [
                r"\bintroduction\b",
                r"\bвведение\b",
                r"\b1\.\s*введение\b",
                r"\b1\.\s*introduction\b"
            ],
            "methodology": [
                r"\bmethodology\b",
                r"\bmethods?\b",
                r"\bметодология\b",
                r"\bметоды?\b",
                r"\b2\.\s*методы?\b"
            ],
            "results": [
                r"\bresults?\b",
                r"\bрезультаты?\b",
                r"\b3\.\s*результаты?\b"
            ],
            "discussion": [
                r"\bdiscussion\b",
                r"\bобсуждение\b",
                r"\b4\.\s*обсуждение\b"
            ],
            "conclusion": [
                r"\bconclusion\b",
                r"\bзаключение\b",
                r"\bвыводы?\b",
                r"\b5\.\s*заключение\b"
            ],
            "references": [
                r"\breferences?\b",
                r"\bbibliography\b",
                r"\bлитература\b",
                r"\bсписок\s+литературы?\b"
            ]
        }
    
    async def analyze(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует структуру статьи"""
        logger.info("Starting structure analysis")
        
        try:
            # Находим секции
            found_sections = self._find_sections(text)
            
            # Анализируем структуру
            structure_quality = self._analyze_structure_quality(found_sections, text)
            
            # Проверяем наличие обязательных секций
            missing_sections = self._check_missing_sections(found_sections)
            
            # Оцениваем связность
            coherence_score = self._assess_coherence(text, found_sections)
            
            result = {
                "found_sections": found_sections,
                "missing_sections": missing_sections,
                "structure_quality": structure_quality,
                "coherence_score": coherence_score,
                "total_sections": len(found_sections),
                "completeness_score": self._calculate_completeness_score(found_sections),
                "recommendations": self._generate_recommendations(found_sections, missing_sections)
            }
            
            logger.info(f"Structure analysis completed. Found {len(found_sections)} sections")
            return result
            
        except Exception as e:
            logger.error(f"Error in structure analysis: {e}")
            return {
                "error": str(e),
                "found_sections": [],
                "missing_sections": self.expected_sections,
                "structure_quality": "poor",
                "coherence_score": 0.0
            }
    
    def _find_sections(self, text: str) -> List[str]:
        """Находит секции в тексте"""
        found_sections = []
        text_lower = text.lower()
        
        for section, patterns in self.section_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    found_sections.append(section)
                    break
        
        return list(set(found_sections))  # Убираем дубли
    
    def _check_missing_sections(self, found_sections: List[str]) -> List[str]:
        """Проверяет отсутствующие обязательные секции"""
        return [section for section in self.expected_sections if section not in found_sections]
    
    def _analyze_structure_quality(self, found_sections: List[str], text: str) -> str:
        """Анализирует качество структуры"""
        completeness = len(found_sections) / len(self.expected_sections)
        
        if completeness >= 0.8:
            return "excellent"
        elif completeness >= 0.6:
            return "good"
        elif completeness >= 0.4:
            return "fair"
        else:
            return "poor"
    
    def _assess_coherence(self, text: str, found_sections: List[str]) -> float:
        """Оценивает связность структуры (простая эвристика)"""
        # Простая оценка на основе длины текста и количества секций
        words_count = len(text.split())
        if len(found_sections) == 0:
            return 0.0
        
        avg_section_length = words_count / len(found_sections)
        
        # Нормализуем относительно ожидаемой длины секции (500-1000 слов)
        if 500 <= avg_section_length <= 1000:
            return 0.8
        elif 300 <= avg_section_length <= 1500:
            return 0.6
        else:
            return 0.4
    
    def _calculate_completeness_score(self, found_sections: List[str]) -> float:
        """Вычисляет оценку полноты структуры"""
        return len(found_sections) / len(self.expected_sections)
    
    def _generate_recommendations(self, found_sections: List[str], missing_sections: List[str]) -> List[str]:
        """Генерирует рекомендации по улучшению структуры"""
        recommendations = []
        
        if missing_sections:
            recommendations.append(f"Добавьте отсутствующие разделы: {', '.join(missing_sections)}")
        
        if "abstract" not in found_sections:
            recommendations.append("Статья должна содержать аннотацию/abstract")
        
        if "introduction" not in found_sections:
            recommendations.append("Добавьте введение для обоснования актуальности исследования")
        
        if "references" not in found_sections:
            recommendations.append("Обязательно включите список литературы")
        
        if len(found_sections) < 4:
            recommendations.append("Структура статьи слишком простая, рассмотрите добавление дополнительных разделов")
        
        return recommendations
    
    def get_prompt_template(self) -> str:
        """Возвращает шаблон промпта для оркестратора"""
        return """
        Based on the structure analysis:
        - Found sections: {found_sections}
        - Missing sections: {missing_sections}
        - Structure quality: {structure_quality}
        - Completeness score: {completeness_score}
        - Recommendations: {recommendations}
        
        Evaluate the structural organization of this academic paper.
        """ 