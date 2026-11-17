"""通知函数：将收到的事件正文作为消息发布到主题（用于解耦或手动触发通知）。"""

import os
import sys
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import config
from common import iam_helper as iam
from common import notify_helper as notify

logger = logging.getLogger(__name__)


def handler(event, context):
    print("=== HANDLER ENTRY ===", flush=True)
    cfg = config.get_config()
    creds = iam.get_credentials(context)

    if isinstance(event, dict):
        subject = event.get("subject", "IAM 访问密钥通知")
        message = event.get("message") or json.dumps(event, ensure_ascii=False)
    else:
        subject = "IAM 访问密钥通知"
        message = str(event)

    notify.publish(creds, cfg, subject, message)
    return {"statusCode": 200, "body": "published"}
