#!/usr/bin/env python3
"""
🧪 Комплексная система тестирования для деплоя бота
Включает unit, integration и end-to-end тесты
"""

import asyncio
import logging
import sys
import os
import json
import tempfile
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import aiohttp
import requests
from unittest.mock import AsyncMock, MagicMock

# Добавляем src директорию в путь
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Результат теста"""
    name: str
    success: bool
    duration: float
    message: str = ""
    details: Dict[str, Any] = None

class TestSuite:
    """Базовый класс для наборов тестов"""
    
    def __init__(self, name: str):
        self.name = name
        self.results: List[TestResult] = []
    
    def add_result(self, result: TestResult):
        """Добавляет результат теста"""
        self.results.append(result)
        
        # Логируем результат
        if result.success:
            logger.info(f"✅ {result.name} - {result.duration:.2f}s")
        else:
            logger.error(f"❌ {result.name} - {result.message}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Возвращает сводку по тестам"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total - passed
        
        return {
            "suite": self.name,
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": passed / total if total > 0 else 0,
            "duration": sum(r.duration for r in self.results)
        }

class UnitTestSuite(TestSuite):
    """Unit тесты компонентов"""
    
    def __init__(self):
        super().__init__("Unit Tests")
    
    async def test_imports(self):
        """Тестирует импорт всех модулей"""
        start_time = time.time()
        
        try:
            # Основные модули
            from core.orchestrator import Orchestrator
            from core.pdf_extractor import PDFExtractor
            from core.agents.structure_agent import StructureAgent
            from core.agents.base_agent import BaseAgent
            
            # Бот модули
            from bot.config import config
            from bot.keyboards import get_main_keyboard
            from bot.handlers import router
            
            # Проверяем что объекты создаются
            orchestrator = Orchestrator()
            pdf_extractor = PDFExtractor()
            structure_agent = StructureAgent()
            
            duration = time.time() - start_time
            self.add_result(TestResult(
                "Import modules", True, duration,
                "Все модули импортируются успешно"
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_result(TestResult(
                "Import modules", False, duration,
                f"Ошибка импорта: {str(e)}"
            ))
    
    async def test_pdf_extractor(self):
        """Тестирует PDF экстрактор"""
        start_time = time.time()
        
        try:
            from core.pdf_extractor import PDFExtractor
            
            extractor = PDFExtractor()
            
            # Тест валидации расширений
            assert extractor.validate_file_extension("test.pdf") == True
            assert extractor.validate_file_extension("test.txt") == False
            assert extractor.validate_file_extension("test.docx") == False
            
            # Тест валидации размеров
            assert extractor.validate_file_size(1024) == True  # 1KB
            assert extractor.validate_file_size(15 * 1024 * 1024) == False  # 15MB
            
            duration = time.time() - start_time
            self.add_result(TestResult(
                "PDF extractor validation", True, duration,
                "PDF экстрактор работает корректно"
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_result(TestResult(
                "PDF extractor validation", False, duration,
                f"Ошибка PDF экстрактора: {str(e)}"
            ))
    
    async def test_structure_agent(self):
        """Тестирует агента структуры"""
        start_time = time.time()
        
        try:
            from core.agents.structure_agent import StructureAgent
            
            agent = StructureAgent()
            
            test_text = """
            Abstract
            This paper presents a novel approach.
            
            1. Introduction
            Machine learning has become important.
            
            2. Methodology
            We used supervised learning.
            
            3. Results
            Our experiments show improvements.
            
            4. Conclusion
            We have presented a new method.
            
            References
            [1] Smith, J. et al. (2023).
            """
            
            # Тест анализа структуры
            results = await agent.analyze(test_text, {"title": "Test Paper"})
            
            # Проверяем что результат содержит ожидаемые поля
            assert isinstance(results, dict)
            assert "found_sections" in results
            assert "structure_quality" in results
            
            duration = time.time() - start_time
            self.add_result(TestResult(
                "Structure agent analysis", True, duration,
                f"Агент нашел {len(results.get('found_sections', []))} разделов"
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_result(TestResult(
                "Structure agent analysis", False, duration,
                f"Ошибка структурного агента: {str(e)}"
            ))
    
    async def test_orchestrator(self):
        """Тестирует оркестратор"""
        start_time = time.time()
        
        try:
            from core.orchestrator import Orchestrator
            from core.agents.structure_agent import StructureAgent
            
            orchestrator = Orchestrator()
            structure_agent = StructureAgent()
            
            # Регистрируем агента
            orchestrator.register_agent("StructureAgent", structure_agent)
            
            # Проверяем что агент зарегистрирован
            assert "StructureAgent" in orchestrator.agents
            
            duration = time.time() - start_time
            self.add_result(TestResult(
                "Orchestrator registration", True, duration,
                "Оркестратор регистрирует агентов корректно"
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_result(TestResult(
                "Orchestrator registration", False, duration,
                f"Ошибка оркестратора: {str(e)}"
            ))
    
    async def run_all(self):
        """Запускает все unit тесты"""
        logger.info(f"🔬 Запуск {self.name}...")
        
        await self.test_imports()
        await self.test_pdf_extractor()
        await self.test_structure_agent()
        await self.test_orchestrator()

class IntegrationTestSuite(TestSuite):
    """Integration тесты между компонентами"""
    
    def __init__(self):
        super().__init__("Integration Tests")
    
    async def test_orchestrator_pipeline(self):
        """Тестирует полный пайплайн оркестратора"""
        start_time = time.time()
        
        try:
            from core.orchestrator import Orchestrator
            from core.agents.structure_agent import StructureAgent
            
            orchestrator = Orchestrator()
            structure_agent = StructureAgent()
            orchestrator.register_agent("StructureAgent", structure_agent)
            
            test_text = """
            Abstract
            This paper presents a comprehensive analysis of machine learning techniques.
            
            1. Introduction
            Machine learning has become increasingly important in recent years.
            
            2. Methodology
            We used a supervised learning approach with neural networks.
            
            3. Results
            Our experiments show significant improvements over baseline methods.
            
            4. Discussion
            The results demonstrate the effectiveness of our approach.
            
            5. Conclusion
            We have presented a new method that achieves state-of-the-art results.
            
            References
            [1] Smith, J. et al. (2023). Machine Learning Advances.
            """
            
            test_metadata = {
                "title": "Test Paper",
                "page_count": 10,
                "author": "Test Author"
            }
            
            # Обрабатываем через оркестратор
            results = await orchestrator.process_paper(test_text, test_metadata)
            
            # Проверяем результат
            assert isinstance(results, dict)
            assert "processing_status" in results
            
            duration = time.time() - start_time
            status = results.get("processing_status", "unknown")
            
            self.add_result(TestResult(
                "Orchestrator pipeline", True, duration,
                f"Пайплайн выполнен со статусом: {status}",
                {"results": results}
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_result(TestResult(
                "Orchestrator pipeline", False, duration,
                f"Ошибка интеграционного теста: {str(e)}"
            ))
    
    async def test_health_check(self):
        """Тестирует health check компонентов"""
        start_time = time.time()
        
        try:
            from core.orchestrator import Orchestrator
            
            orchestrator = Orchestrator()
            
            # Выполняем health check
            health = await orchestrator.health_check()
            
            # Проверяем базовую структуру ответа
            assert isinstance(health, dict)
            
            duration = time.time() - start_time
            self.add_result(TestResult(
                "Component health check", True, duration,
                f"Health check выполнен: {health}",
                {"health": health}
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_result(TestResult(
                "Component health check", False, duration,
                f"Ошибка health check: {str(e)}"
            ))
    
    async def run_all(self):
        """Запускает все integration тесты"""
        logger.info(f"🔗 Запуск {self.name}...")
        
        await self.test_orchestrator_pipeline()
        await self.test_health_check()

class DeploymentTestSuite(TestSuite):
    """Тесты деплоя и сервисов"""
    
    def __init__(self):
        super().__init__("Deployment Tests")
        self.llm_service_url = os.getenv("LLM_SERVICE_URL", "http://localhost:8000")
        self.docker_compose_file = "docker-compose.production.yml"
    
    async def test_docker_containers(self):
        """Тестирует состояние Docker контейнеров"""
        start_time = time.time()
        
        try:
            # Проверяем статус контейнеров
            result = subprocess.run(
                ["docker-compose", "-f", self.docker_compose_file, "ps"],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Ошибка выполнения docker-compose ps: {result.stderr}")
            
            output = result.stdout
            
            # Проверяем что контейнеры запущены
            if "Up" not in output:
                raise Exception("Контейнеры не запущены")
            
            duration = time.time() - start_time
            self.add_result(TestResult(
                "Docker containers status", True, duration,
                "Все контейнеры запущены и работают"
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_result(TestResult(
                "Docker containers status", False, duration,
                f"Ошибка проверки контейнеров: {str(e)}"
            ))
    
    async def test_llm_service_health(self):
        """Тестирует доступность LLM сервиса"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.llm_service_url}/health",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        raise Exception(f"LLM service health check failed: {response.status}")
                    
                    health_data = await response.json()
                    
                    duration = time.time() - start_time
                    self.add_result(TestResult(
                        "LLM service health", True, duration,
                        f"LLM сервис доступен: {health_data}",
                        {"health": health_data}
                    ))
                    
        except Exception as e:
            duration = time.time() - start_time
            self.add_result(TestResult(
                "LLM service health", False, duration,
                f"LLM сервис недоступен: {str(e)}"
            ))
    
    async def test_llm_service_models(self):
        """Тестирует доступность моделей в LLM сервисе"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.llm_service_url}/models",
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Models endpoint failed: {response.status}")
                    
                    models_data = await response.json()
                    
                    if not models_data.get("success"):
                        raise Exception(f"Models request failed: {models_data.get('error')}")
                    
                    models = models_data.get("models", [])
                    
                    duration = time.time() - start_time
                    self.add_result(TestResult(
                        "LLM service models", True, duration,
                        f"Доступно моделей: {len(models)} - {models}",
                        {"models": models}
                    ))
                    
        except Exception as e:
            duration = time.time() - start_time
            self.add_result(TestResult(
                "LLM service models", False, duration,
                f"Ошибка получения моделей: {str(e)}"
            ))
    
    async def test_llm_service_review(self):
        """Тестирует endpoint рецензирования"""
        start_time = time.time()
        
        try:
            test_payload = {
                "text": "This is a test paper about machine learning approaches.",
                "metadata": {"title": "Test Paper", "author": "Test Author"}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.llm_service_url}/review",
                    json=test_payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Review endpoint failed: {response.status} - {error_text}")
                    
                    review_data = await response.json()
                    
                    if not review_data.get("success"):
                        raise Exception(f"Review failed: {review_data.get('error')}")
                    
                    results = review_data.get("results", {})
                    
                    duration = time.time() - start_time
                    self.add_result(TestResult(
                        "LLM service review", True, duration,
                        f"Рецензирование выполнено за {duration:.1f}s",
                        {"results": results}
                    ))
                    
        except Exception as e:
            duration = time.time() - start_time
            self.add_result(TestResult(
                "LLM service review", False, duration,
                f"Ошибка рецензирования: {str(e)}"
            ))
    
    async def test_resource_usage(self):
        """Тестирует использование ресурсов"""
        start_time = time.time()
        
        try:
            # Получаем статистику Docker
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", 
                 "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Ошибка docker stats: {result.stderr}")
            
            stats = result.stdout
            
            duration = time.time() - start_time
            self.add_result(TestResult(
                "Resource usage", True, duration,
                "Статистика ресурсов получена",
                {"stats": stats}
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_result(TestResult(
                "Resource usage", False, duration,
                f"Ошибка получения статистики: {str(e)}"
            ))
    
    async def run_all(self):
        """Запускает все deployment тесты"""
        logger.info(f"🚀 Запуск {self.name}...")
        
        await self.test_docker_containers()
        await self.test_llm_service_health()
        await self.test_llm_service_models()
        await self.test_llm_service_review()
        await self.test_resource_usage()

class EndToEndTestSuite(TestSuite):
    """End-to-end тесты полного функционала"""
    
    def __init__(self):
        super().__init__("End-to-End Tests")
        self.llm_service_url = os.getenv("LLM_SERVICE_URL", "http://localhost:8000")
    
    async def test_full_paper_processing(self):
        """Тестирует полную обработку статьи"""
        start_time = time.time()
        
        try:
            # Имитируем полную научную статью
            full_paper_text = """
            Title: Advanced Machine Learning Techniques for Text Analysis
            
            Abstract
            This paper presents a comprehensive analysis of advanced machine learning 
            techniques specifically designed for text analysis applications. We propose 
            a novel approach that combines neural networks with traditional NLP methods 
            to achieve superior performance in document classification and sentiment analysis.
            
            1. Introduction
            Natural language processing has become increasingly important in the era of 
            big data. Traditional approaches often struggle with the complexity and 
            nuance of human language. This paper addresses these challenges by proposing 
            a hybrid approach that leverages both modern deep learning techniques and 
            established linguistic principles.
            
            2. Related Work
            Previous work in this area has focused primarily on either deep learning 
            approaches or traditional NLP methods. Smith et al. (2022) demonstrated 
            the effectiveness of transformer models for text classification. Johnson 
            and Brown (2023) showed that traditional feature engineering can still 
            provide valuable insights.
            
            3. Methodology
            Our approach consists of three main components: (1) preprocessing pipeline 
            that normalizes text and extracts linguistic features, (2) neural network 
            architecture that processes these features, and (3) post-processing module 
            that refines the final predictions.
            
            3.1 Preprocessing Pipeline
            The preprocessing pipeline includes tokenization, stemming, and feature 
            extraction. We use a combination of TF-IDF vectors and word embeddings 
            to represent textual data.
            
            3.2 Neural Network Architecture
            Our neural network consists of multiple layers including embedding layers, 
            LSTM layers, and dense layers. The architecture is designed to capture 
            both local and global patterns in the text.
            
            4. Experiments
            We conducted extensive experiments on three benchmark datasets: Reuters-21578, 
            20 Newsgroups, and IMDB movie reviews. Our method was compared against 
            several baseline approaches including SVM, Random Forest, and BERT.
            
            4.1 Dataset Description
            Reuters-21578 contains 21,578 news articles across multiple categories. 
            20 Newsgroups consists of 20,000 newsgroup posts. IMDB dataset includes 
            50,000 movie reviews with sentiment labels.
            
            4.2 Experimental Setup
            All experiments were run on a machine with 32GB RAM and NVIDIA V100 GPU. 
            We used 80% of data for training, 10% for validation, and 10% for testing.
            
            5. Results
            Our proposed method achieved state-of-the-art performance on all three 
            datasets. On Reuters-21578, we achieved 94.2% accuracy, compared to 
            91.5% for BERT baseline. On 20 Newsgroups, our accuracy was 89.7% vs 
            87.3% for the best baseline.
            
            5.1 Ablation Study
            We conducted ablation studies to understand the contribution of each 
            component. The preprocessing pipeline contributed 2.1% improvement, 
            the neural architecture added 1.8%, and post-processing provided 0.7%.
            
            6. Discussion
            The results demonstrate that combining traditional NLP techniques with 
            modern deep learning approaches can lead to significant improvements. 
            The preprocessing pipeline is particularly important for handling noisy 
            real-world text data.
            
            6.1 Limitations
            Our approach has some limitations. The computational cost is higher than 
            simple baselines. The method requires careful hyperparameter tuning. 
            Performance on very short texts (< 10 words) is limited.
            
            7. Conclusion
            We have presented a novel hybrid approach for text analysis that combines 
            the strengths of traditional NLP and modern deep learning. Our experimental 
            results demonstrate the effectiveness of this approach across multiple 
            benchmark datasets. Future work will focus on reducing computational costs 
            and improving performance on short texts.
            
            Acknowledgments
            We thank the anonymous reviewers for their valuable feedback. This work 
            was supported by grants from NSF and NIH.
            
            References
            [1] Smith, A., Jones, B., and Wilson, C. (2022). "Transformer Models for 
                Text Classification." Proceedings of ICML, pp. 1234-1245.
                
            [2] Johnson, D. and Brown, E. (2023). "Traditional Features in Modern NLP." 
                Journal of AI Research, vol. 45, pp. 67-89.
                
            [3] Chen, F., Wang, G., and Li, H. (2021). "Deep Learning for Sentiment 
                Analysis." Neural Networks, vol. 128, pp. 45-62.
                
            [4] Davis, I. and Miller, J. (2020). "Preprocessing Techniques for Text 
                Mining." Data Mining and Knowledge Discovery, vol. 34, pp. 123-145.
            """
            
            metadata = {
                "title": "Advanced Machine Learning Techniques for Text Analysis",
                "author": "Test Author",
                "page_count": 12,
                "journal": "Test Journal",
                "year": 2024
            }
            
            # Отправляем на обработку
            payload = {
                "text": full_paper_text,
                "metadata": metadata
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.llm_service_url}/review",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)  # 2 минуты
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"E2E test failed: {response.status} - {error_text}")
                    
                    result = await response.json()
                    
                    if not result.get("success"):
                        raise Exception(f"E2E processing failed: {result.get('error')}")
                    
                    results = result.get("results", {})
                    final_review = results.get("final_review", "")
                    
                    # Проверяем качество результата
                    if len(final_review) < 100:
                        logger.warning("Финальная рецензия слишком короткая")
                    
                    duration = time.time() - start_time
                    self.add_result(TestResult(
                        "Full paper processing", True, duration,
                        f"Полная обработка завершена за {duration:.1f}s, рецензия: {len(final_review)} символов",
                        {
                            "review_length": len(final_review),
                            "processing_status": results.get("processing_status"),
                            "agents_used": list(results.get("agent_results", {}).keys())
                        }
                    ))
                    
        except Exception as e:
            duration = time.time() - start_time
            self.add_result(TestResult(
                "Full paper processing", False, duration,
                f"Ошибка E2E теста: {str(e)}"
            ))
    
    async def run_all(self):
        """Запускает все E2E тесты"""
        logger.info(f"🎯 Запуск {self.name}...")
        
        await self.test_full_paper_processing()

class TestRunner:
    """Основной класс для запуска всех тестов"""
    
    def __init__(self):
        self.suites: List[TestSuite] = []
        self.start_time = time.time()
    
    def add_suite(self, suite: TestSuite):
        """Добавляет набор тестов"""
        self.suites.append(suite)
    
    async def run_all(self, quick_mode: bool = False):
        """Запускает все тесты"""
        logger.info("🧪 Запуск комплексного тестирования системы")
        logger.info("=" * 60)
        
        # Unit тесты
        unit_tests = UnitTestSuite()
        await unit_tests.run_all()
        self.add_suite(unit_tests)
        
        # Integration тесты
        integration_tests = IntegrationTestSuite()
        await integration_tests.run_all()
        self.add_suite(integration_tests)
        
        # Deployment тесты (только если не quick mode)
        if not quick_mode:
            deployment_tests = DeploymentTestSuite()
            await deployment_tests.run_all()
            self.add_suite(deployment_tests)
            
            # E2E тесты
            e2e_tests = EndToEndTestSuite()
            await e2e_tests.run_all()
            self.add_suite(e2e_tests)
        
        # Выводим результаты
        self.print_summary()
        
        return self.is_all_passed()
    
    def print_summary(self):
        """Выводит сводку по всем тестам"""
        total_duration = time.time() - self.start_time
        
        print("\n" + "=" * 60)
        print("📊 СВОДКА ПО ТЕСТИРОВАНИЮ")
        print("=" * 60)
        
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for suite in self.suites:
            summary = suite.get_summary()
            total_tests += summary["total"]
            total_passed += summary["passed"]
            total_failed += summary["failed"]
            
            status = "✅" if summary["failed"] == 0 else "❌"
            print(f"{status} {summary['suite']}: {summary['passed']}/{summary['total']} "
                  f"({summary['success_rate']:.1%}) - {summary['duration']:.2f}s")
        
        print("-" * 60)
        overall_success = total_failed == 0
        status = "✅ УСПЕШНО" if overall_success else "❌ ЕСТЬ ОШИБКИ"
        
        print(f"{status}: {total_passed}/{total_tests} тестов пройдено "
              f"({total_passed/total_tests:.1%}) за {total_duration:.2f}s")
        
        if total_failed > 0:
            print(f"\n⚠️  Не пройдено тестов: {total_failed}")
            print("Проверьте логи выше для деталей")
        
        print("=" * 60)
    
    def is_all_passed(self) -> bool:
        """Проверяет что все тесты прошли"""
        for suite in self.suites:
            summary = suite.get_summary()
            if summary["failed"] > 0:
                return False
        return True

async def main():
    """Основная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Тестирование системы бота")
    parser.add_argument("--quick", action="store_true", 
                       help="Быстрый режим (только unit и integration тесты)")
    parser.add_argument("--unit-only", action="store_true",
                       help="Только unit тесты")
    parser.add_argument("--deployment-only", action="store_true",
                       help="Только deployment тесты")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    try:
        if args.unit_only:
            unit_tests = UnitTestSuite()
            await unit_tests.run_all()
            runner.add_suite(unit_tests)
        elif args.deployment_only:
            deployment_tests = DeploymentTestSuite()
            await deployment_tests.run_all()
            runner.add_suite(deployment_tests)
        else:
            success = await runner.run_all(quick_mode=args.quick)
            
        runner.print_summary()
        
        # Возвращаем код выхода
        if runner.is_all_passed():
            print("\n🎉 Все тесты пройдены! Система готова к работе.")
            return 0
        else:
            print("\n💥 Есть проблемы! Проверьте результаты тестов.")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
        return 1
    except Exception as e:
        print(f"\n💥 Критическая ошибка при тестировании: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 