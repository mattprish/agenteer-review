from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def format_review(results: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
    """
    Форматирует результаты анализа для отображения в Telegram
    
    Args:
        results: Результаты анализа от оркестратора
        metadata: Метаданные статьи (опционально, если нет в results)
        
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
        
        # Результаты анализа агентов
        agent_results = results.get("agent_results", {})
        
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
            formatted_parts.append("📝 *Итоговая рецензия:*\n")
            formatted_parts.append(final_review)
        
        return "\n".join(formatted_parts)
        
    except Exception as e:
        logger.error(f"Error formatting review: {e}")
        return format_error_message(f"Ошибка форматирования: {str(e)}")

def format_structure_analysis(structure_results: Dict[str, Any]) -> str:
    """Форматирует результаты анализа структуры"""
    if "error" in structure_results:
        return f"❌ *Ошибка анализа структуры:* {structure_results['error']}\n"
    
    parts = ["🏗 *Анализ структуры статьи:*"]
    
    # Найденные разделы
    found_sections = structure_results.get("found_sections", [])
    if found_sections:
        parts.append(f"✅ *Найденные разделы:* {', '.join(found_sections)}")
    else:
        parts.append("❌ *Разделы не найдены*")
    
    # Отсутствующие разделы
    missing_sections = structure_results.get("missing_sections", [])
    if missing_sections:
        parts.append(f"⚠️ *Отсутствующие разделы:* {', '.join(missing_sections)}")
    
    # Качество структуры
    quality = structure_results.get("structure_quality", "unknown")
    quality_emoji = get_quality_emoji(quality)
    parts.append(f"{quality_emoji} *Качество структуры:* {quality}")
    
    # Оценка полноты
    completeness = structure_results.get("completeness_score", 0)
    if isinstance(completeness, (int, float)):
        parts.append(f"📊 *Полнота структуры:* {completeness:.1%}")
    
    # Рекомендации
    recommendations = structure_results.get("recommendations", [])
    if recommendations:
        parts.append("\n💡 *Рекомендации по структуре:*")
        for i, rec in enumerate(recommendations[:3], 1):  # Ограничиваем 3 рекомендациями
            parts.append(f"{i}. {rec}")
    
    parts.append("")
    return "\n".join(parts)

def format_summary_analysis(summary_results: Dict[str, Any]) -> str:
    """Форматирует результаты анализа содержания"""
    if "error" in summary_results:
        return f"❌ *Ошибка анализа содержания:* {summary_results['error']}\n"
    
    parts = ["📚 *Анализ содержания статьи:*"]
    
    # Качество резюме
    summary_quality = summary_results.get("summary_quality", "unknown")
    quality_emoji = get_quality_emoji(summary_quality)
    parts.append(f"{quality_emoji} *Качество резюме:* {summary_quality}")
    
    # Ключевые темы
    key_topics = summary_results.get("key_topics", [])
    if key_topics:
        parts.append(f"🔍 *Ключевые темы:* {', '.join(key_topics[:5])}")
    
    # Степень сжатия
    compression_ratio = summary_results.get("compression_ratio", 0)
    if isinstance(compression_ratio, (int, float)):
        parts.append(f"📏 *Степень сжатия:* {compression_ratio:.1%}")
    
    # Резюме статьи (если не слишком длинное)
    summary_text = summary_results.get("summary", "")
    if summary_text and len(summary_text) < 800:
        parts.append(f"\n📄 *Краткое резюме:*\n{summary_text[:600]}...")
    
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