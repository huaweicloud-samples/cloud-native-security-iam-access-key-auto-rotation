"""运行期配置：从函数环境变量读取轮转参数。"""

import os


def get_config():
    """读取函数环境变量，返回配置字典。"""
    return {
        "region": os.environ.get("REGION", "cn-north-4"),
        "obs_bucket": os.environ.get("OBS_BUCKET", ""),
        "notify_topic_urn": os.environ.get("NOTIFY_TOPIC_URN", ""),
        "domain_id": os.environ.get("DOMAIN_ID", ""),
        "rotation_period_days": int(os.environ.get("ROTATION_PERIOD_DAYS", "90")),
        "inactive_period_days": int(os.environ.get("INACTIVE_PERIOD_DAYS", "100")),
        "delete_period_days": int(os.environ.get("DELETE_PERIOD_DAYS", "110")),
        "target_user_filter": os.environ.get("TARGET_USER_FILTER", ""),
    }
