from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def format_review(results: Dict[str, Any], metadata: Dict[str, Any] = None, verbose: bool = False) -> str:
    """
    Форматирует результаты анализа для отображения в Telegram
    
    Args:
        results: Результаты анализа от оркестратора
        metadata: Метаданные статьи (опционально, если нет в results)
        verbose: Показывать ли детальные результаты агентов
        
    Returns:
        str: Отформатированный текст рецензии
    """
    try:
        if results.get("processing_status") == "error":
            return format_error_message(results.get("error", "Unknown error"))
        
        formatted_parts = []
        
        # Заголовок
        formatted_parts.append("📄 *Автоматическая рецензия научной статьи*\n")
        
        # Метаданные статьи
        paper_metadata = metadata or results.get("metadata", {})
        if paper_metadata:
            formatted_parts.append("📋 *Информация о статье:*")
            
            if paper_metadata.get("title"):
                title = paper_metadata["title"]
                if len(title) > 100:
                    title = title[:100] + "..."
                formatted_parts.append(f"• *Название:* {title}")
            
            if paper_metadata.get("author"):
                formatted_parts.append(f"• *Автор:* {paper_metadata['author']}")
            
            if paper_metadata.get("page_count"):
                formatted_parts.append(f"• *Количество страниц:* {paper_metadata['page_count']}")
            
            formatted_parts.append("")
        
        if verbose:
            # Результаты анализа агентов (детальная информация)
            agent_results = results.get("agent_results", {})
            
            formatted_parts.append("🔍 *Детальный анализ агентов:*\n")
            
            # Структурный анализ
            if "StructureAgent" in agent_results:
                structure_formatted = format_structure_analysis(agent_results["StructureAgent"])
                formatted_parts.append(structure_formatted)
            
            # Анализ содержания (Summary Agent)
            if "SummaryAgent" in agent_results:
                summary_formatted = format_summary_analysis(agent_results["SummaryAgent"])
                formatted_parts.append(summary_formatted)
            
        # Финальная рецензия
        final_review = results.get("final_review", "")
        if final_review:
            formatted_parts.append("📝 *Рецензия:*\n")
            formatted_parts.append(final_review)
        
        return "\n".join(formatted_parts)
        
    except Exception as e:
        logger.error(f"Error formatting review: {e}")
        return format_error_message(f"Ошибка форматирования: {str(e)}")

def format_structure_analysis(structure_results) -> str:
    """Форматирует результаты анализа структуры"""
    parts = ["🏗 *Анализ структуры статьи:*"]
    
    # Агент теперь возвращает сырой текст LLM
    if isinstance(structure_results, str):
        if structure_results.startswith("ERROR:"):
            parts.append(f"❌ *Ошибка:* {structure_results[6:].strip()}")
        else:
            # Показываем первые 400 символов анализа
            analysis_text = structure_results[:400] + "..." if len(structure_results) > 400 else structure_results
            parts.append(f"📄 *Анализ:*\n{analysis_text}")
    elif isinstance(structure_results, dict) and "result" in structure_results:
        result_text = structure_results["result"]
        if result_text.startswith("ERROR:"):
            parts.append(f"❌ *Ошибка:* {result_text[6:].strip()}")
        else:
            analysis_text = result_text[:400] + "..." if len(result_text) > 400 else result_text
            parts.append(f"📄 *Анализ:*\n{analysis_text}")
    else:
        parts.append("❌ *Неизвестный формат результата*")
    
    parts.append("")
    return "\n".join(parts)

def format_summary_analysis(summary_results) -> str:
    """Форматирует результаты анализа содержания"""
    parts = ["📚 *Анализ содержания статьи:*"]
    
    # Агент теперь возвращает сырой текст LLM
    if isinstance(summary_results, str):
        if summary_results.startswith("ERROR:"):
            parts.append(f"❌ *Ошибка:* {summary_results[6:].strip()}")
        else:
            # Показываем первые 500 символов резюме
            summary_text = summary_results[:500] + "..." if len(summary_results) > 500 else summary_results
            parts.append(f"📖 *Резюме:*\n{summary_text}")
    elif isinstance(summary_results, dict) and "result" in summary_results:
        result_text = summary_results["result"]
        if result_text.startswith("ERROR:"):
            parts.append(f"❌ *Ошибка:* {result_text[6:].strip()}")
        else:
            summary_text = result_text[:500] + "..." if len(result_text) > 500 else result_text
            parts.append(f"📖 *Резюме:*\n{summary_text}")
    else:
        parts.append("❌ *Неизвестный формат результата*")
    
    parts.append("")
    return "\n".join(parts)

def get_quality_emoji(quality: str) -> str:
    """Возвращает эмодзи для качества"""
    quality_emojis = {
        "excellent": "🌟",
        "good": "✅", 
        "fair": "⚠️",
        "poor": "❌",
        "unknown": "❓"
    }
    return quality_emojis.get(quality, "❓")

def format_error_message(error: str) -> str:
    """Форматирует сообщение об ошибке"""
    return f"""❌ *Произошла ошибка при анализе статьи*

🔍 *Детали ошибки:*
{error}

💡 *Возможные причины:*
• Файл поврежден или не является PDF
• Проблемы с извлечением текста
• Временные проблемы с сервисом

🔄 Попробуйте загрузить файл еще раз."""

def format_progress_message(stage: str) -> str:
    """Форматирует сообщение о прогрессе обработки"""
    stage_messages = {
        "downloading": "📥 Скачиваю файл...",
        "extracting": "📄 Извлекаю текст из PDF...",
        "analyzing_structure": "🏗 Анализирую структуру статьи...",
        "analyzing_content": "📚 Анализирую содержание...",
        "generating_review": "📝 Генерирую рецензию...",
        "finalizing": "✅ Завершаю обработку..."
    }
    
    return stage_messages.get(stage, f"🔄 {stage}...")

def truncate_text(text: str, max_length: int = 4000) -> str:
    """
    Обрезает текст до максимальной длины для Telegram
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        
    Returns:
        str: Обрезанный текст
    """
    if len(text) <= max_length:
        return text
    
    # Обрезаем с многоточием
    return text[:max_length - 3] + "..."

def escape_markdown(text: str) -> str:
    """Экранирует специальные символы Markdown для Telegram"""
    # Символы, которые нужно экранировать в Telegram MarkdownV2
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    
    return text 