import logging
from logging.handlers import RotatingFileHandler

# formatter
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# file handler (creates app.log in project root, max 5MB, keeps 3 backups)
file_handler = RotatingFileHandler("app.log", maxBytes=5 * 1024 * 1024, backupCount=3)
file_handler.setFormatter(formatter)

# logger setup
logger = logging.getLogger("app")
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
logger.addHandler(file_handler)