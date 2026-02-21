import logging
from datetime import datetime
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR,exist_ok=True)

log_filename = f"{LOG_DIR}/contract_analyzer_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level = logging.INFO,
    format = "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers = [
        logging.FileHandler(log_filename),
        logging.StreamHandler() ##still prints minimal info to console
    ]
)

logger = logging.getLogger("contract_analyzer")