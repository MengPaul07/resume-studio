import logging
import json
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def log_action(user_id: str, action: str, resource_type: str, details: dict = None):
    """记录用户操作日志"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "action": action,
        "resource": resource_type,
        "details": details or {}
    }
    logger.info(json.dumps(log_entry, ensure_ascii=False))
