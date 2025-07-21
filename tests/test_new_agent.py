#!/usr/bin/env python3
"""
🆕 Тест для проверки новых агентов после их добавления
Этот скрипт проверяет что новый агент корректно интегрируется в систему
"""

import asyncio
import logging
import sys
import os
import importlib
from pathlib import Path
from typing import List, Dict, Any

# Добавляем src директорию в путь
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NewAgentTester:
    """Тестер для новых агентов"""
    
    def __init__(self):
        # Путь к агентам относительно корня проекта
        project_root = Path(__file__).parent.parent
        self.agents_dir = project_root / "src" / "core" / "agents"
        self.known_agents = {"base_agent.py", "structure_agent.py", "summary_agent.py", "__init__.py"}
    
    def find_new_agents(self) -> List[str]:
        """Находит новые агенты в директории"""
        if not self.agents_dir.exists():
            logger.error(f"Директория агентов не найдена: {self.agents_dir}")
            return []
        
        all_files = set(f.name for f in self.agents_dir.glob("*.py"))
        new_agents = all_files - self.known_agents
        
        logger.info(f"Найдено агентов: {len(all_files)}")
        logger.info(f"Новых агентов: {len(new_agents)}")
        
        return list(new_agents)
    
    async def test_agent_import(self, agent_file: str) -> bool:
        """Тестирует импорт агента"""
        try:
            module_name = agent_file.replace(".py", "")
            full_module_name = f"core.agents.{module_name}"
            
            # Импортируем модуль
            module = importlib.import_module(full_module_name)
            logger.info(f"✅ Модуль {module_name} импортирован успешно")
            
            # Ищем класс агента (должен заканчиваться на "Agent", но не быть BaseAgent)
            agent_classes = [
                name for name in dir(module) 
                if name.endswith("Agent") and not name.startswith("_") and name != "BaseAgent"
            ]
            
            if not agent_classes:
                logger.warning(f"⚠️ В модуле {module_name} не найдено классов агентов")
                return False
            
            logger.info(f"📋 Найдены классы агентов: {agent_classes}")
            
            # Проверяем каждый класс
            for class_name in agent_classes:
                agent_class = getattr(module, class_name)
                
                # Проверяем что это класс
                if not isinstance(agent_class, type):
                    continue
                
                # Пытаемся создать экземпляр
                try:
                    agent_instance = agent_class()
                    logger.info(f"✅ Экземпляр {class_name} создан успешно")
                    
                    # Проверяем наличие метода analyze
                    if hasattr(agent_instance, 'analyze'):
                        logger.info(f"✅ Метод analyze найден в {class_name}")
                    else:
                        logger.warning(f"⚠️ Метод analyze не найден в {class_name}")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка создания экземпляра {class_name}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка импорта {agent_file}: {e}")
            return False
    
    async def test_agent_integration(self, agent_file: str) -> bool:
        """Тестирует интеграцию агента с оркестратором"""
        try:
            from core.orchestrator import Orchestrator
            
            module_name = agent_file.replace(".py", "")
            full_module_name = f"core.agents.{module_name}"
            
            # Импортируем модуль и находим классы агентов
            module = importlib.import_module(full_module_name)
            agent_classes = [
                name for name in dir(module) 
                if name.endswith("Agent") and not name.startswith("_") and name != "BaseAgent"
            ]
            
            orchestrator = Orchestrator()
            
            for class_name in agent_classes:
                agent_class = getattr(module, class_name)
                
                if not isinstance(agent_class, type):
                    continue
                
                try:
                    # Создаем экземпляр и регистрируем в оркестраторе
                    agent_instance = agent_class()
                    orchestrator.register_agent(class_name, agent_instance)
                    
                    # Проверяем что агент зарегистрирован
                    if class_name in orchestrator.agents:
                        logger.info(f"✅ Агент {class_name} зарегистрирован в оркестраторе")
                    else:
                        logger.error(f"❌ Агент {class_name} не зарегистрирован")
                        return False
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка регистрации агента {class_name}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка интеграции агента {agent_file}: {e}")
            return False
    
    async def test_agent_functionality(self, agent_file: str) -> bool:
        """Тестирует функциональность агента"""
        try:
            module_name = agent_file.replace(".py", "")
            full_module_name = f"core.agents.{module_name}"
            
            module = importlib.import_module(full_module_name)
            agent_classes = [
                name for name in dir(module) 
                if name.endswith("Agent") and not name.startswith("_") and name != "BaseAgent"
            ]
            
            test_text = """
            Abstract
            This paper presents a novel approach to machine learning.
            
            1. Introduction
            Machine learning has become increasingly important.
            
            2. Methodology  
            We used supervised learning with neural networks.
            
            3. Results
            Our experiments show significant improvements.
            
            4. Conclusion
            We have presented a new method with state-of-the-art results.
            
            References
            [1] Smith, J. et al. (2023). ML Advances.
            """
            
            test_metadata = {
                "title": "Test Paper",
                "author": "Test Author",
                "page_count": 5
            }
            
            for class_name in agent_classes:
                agent_class = getattr(module, class_name)
                
                if not isinstance(agent_class, type):
                    continue
                
                try:
                    agent_instance = agent_class()
                    
                    # Проверяем наличие и вызов метода analyze
                    if hasattr(agent_instance, 'analyze'):
                        results = await agent_instance.analyze(test_text, test_metadata)
                        
                        # Проверяем результат
                        if isinstance(results, dict):
                            logger.info(f"✅ Агент {class_name} вернул корректный результат")
                            logger.info(f"📊 Ключи результата: {list(results.keys())}")
                        else:
                            logger.warning(f"⚠️ Агент {class_name} вернул некорректный тип результата")
                            return False
                    else:
                        logger.warning(f"⚠️ У агента {class_name} нет метода analyze")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка функциональности агента {class_name}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования функциональности {agent_file}: {e}")
            return False
    
    async def test_all_new_agents(self) -> bool:
        """Тестирует все новые агенты"""
        new_agents = self.find_new_agents()
        
        if not new_agents:
            logger.info("🎉 Новых агентов не найдено")
            return True
        
        logger.info(f"🧪 Тестирование {len(new_agents)} новых агентов...")
        
        all_passed = True
        
        for agent_file in new_agents:
            logger.info(f"\n🔍 Тестирование агента: {agent_file}")
            logger.info("-" * 50)
            
            # Тест импорта
            if not await self.test_agent_import(agent_file):
                logger.error(f"❌ Агент {agent_file} не прошел тест импорта")
                all_passed = False
                continue
            
            # Тест интеграции
            if not await self.test_agent_integration(agent_file):
                logger.error(f"❌ Агент {agent_file} не прошел тест интеграции")
                all_passed = False
                continue
            
            # Тест функциональности
            if not await self.test_agent_functionality(agent_file):
                logger.error(f"❌ Агент {agent_file} не прошел тест функциональности")
                all_passed = False
                continue
            
            logger.info(f"✅ Агент {agent_file} прошел все тесты")
        
        return all_passed

async def main():
    """Основная функция тестирования новых агентов"""
    logger.info("🆕 Тестирование новых агентов")
    logger.info("=" * 50)
    
    tester = NewAgentTester()
    
    try:
        success = await tester.test_all_new_agents()
        
        if success:
            logger.info("\n🎉 Все новые агенты прошли тестирование!")
            logger.info("✅ Система готова к работе с новыми агентами")
            return 0
        else:
            logger.error("\n💥 Некоторые агенты не прошли тестирование!")
            logger.error("❌ Проверьте ошибки выше")
            return 1
            
    except Exception as e:
        logger.error(f"\n💥 Критическая ошибка: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 