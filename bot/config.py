import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Models
    ORCHESTRATOR_MODEL: str = "llama3.2:3b"
    STRUCTURE_MODEL: str = "allenai/scibert_scivocab_uncased"
    
    # Limits
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    MAX_PROCESSING_TIME: int = 120  # seconds
    
    # Paths
    TEMP_DIR: str = "./temp"
    MODEL_CACHE_DIR: str = "./models"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    def __post_init__(self):
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")

config = Config() 