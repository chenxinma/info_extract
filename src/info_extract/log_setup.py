import logging
import os

log_dir = './logs/'
os.makedirs(log_dir, exist_ok=True)

def setup_logging():
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'info_extract.log'), encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
