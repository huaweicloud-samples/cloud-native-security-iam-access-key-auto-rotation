"""清单函数：定期列举域下 IAM 用户并输出清单（可选写入对象存储）。"""

import os
import sys
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import config
from common import iam_helper as iam

logger = logging.getLogger(__name__)


def write_to_obs(context, cfg, data):
    """尝试将清单写入对象存储；需为委托主体配置桶策略，失败时不阻断主流程。"""
    try:
        from obs import ObsClient

        ak = context.getSecurityAccessKey()
        sk = context.getSecuritySecretKey()
        token = context.getSecurityToken()
        server = "https://obs.%s.myhuaweicloud.com" % cfg["region"]
        oc = ObsClient(
            access_key_id=ak,
            secret_access_key=sk,
            security_token=token,
            server=server,
        )
        oc.putObject(cfg["obs_bucket"], "inventory/users.json", json.dumps(data, ensure_ascii=False))
        logger.info("用户清单已写入对象存储")
    except Exception as exc:  # noqa: BLE001
        logger.warning("写入对象存储失败（需配置桶策略允许委托主体）：%s", exc)


def handler(event, context):
    print("=== HANDLER ENTRY ===", flush=True)
    cfg = config.get_config()
    creds = iam.get_credentials(context)
    client = iam.build_iam_client(cfg["region"], creds)

    users = iam.list_domain_users(client, cfg.get("domain_id"))
    inventory = [
        {"id": getattr(u, "id", None), "name": getattr(u, "name", None)}
        for u in users
    ]

    if cfg.get("obs_bucket"):
        try:
            write_to_obs(context, cfg, inventory)
        except Exception as exc:  # noqa: BLE001
            logger.error("清单落盘异常：%s", exc)

    return {
        "statusCode": 200,
        "body": json.dumps(inventory, ensure_ascii=False),
    }
