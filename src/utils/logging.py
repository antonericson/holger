import logging

def setup_logging(level_str: str):
    logger = logging.getLogger('holger')
    level = logging.getLevelNamesMapping().get(level_str)
    logger.setLevel(level)
    
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger
