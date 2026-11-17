"""轮转函数：依据密钥年龄创建/禁用/删除 IAM 访问密钥，并通过消息通知服务披露结果。"""

import os
import sys
import json
import datetime
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import config
from common import iam_helper as iam
from common import notify_helper as notify
from common import secret_helper as secret

logger = logging.getLogger(__name__)


def rotate_one_user(client, cfg, user):
    """对单个用户执行轮转决策，返回动作列表。"""
    uid = getattr(user, "id", None)
    name = getattr(user, "name", None) or getattr(user, "username", None)
    if not uid:
        return []

    keys = iam.list_user_access_keys(client, uid)
    now = datetime.datetime.now(datetime.timezone.utc)

    key_info = []
    for k in keys:
        ct = iam.parse_create_time(getattr(k, "create_time", None))
        age = (now - ct).days if ct else 9999
        key_info.append(
            {
                "access": getattr(k, "access", None),
                "status": getattr(k, "status", None),
                "age": age,
            }
        )

    active = [x for x in key_info if x["status"] == "ACTIVE"]
    newest_age = max([x["age"] for x in key_info], default=0)

    actions = []

    # 1) 必要时新建一把密钥
    if iam.should_create_new(newest_age, len(active), cfg):
        try:
            new_cred = iam.create_access_key(client, uid)
            actions.append(
                {
                    "user": name,
                    "action": "create",
                    "access": getattr(new_cred, "access", None),
                }
            )
            # 新密钥明文一次性披露并可选入库
            plain = getattr(new_cred, "secret", None)
            if plain:
                actions.append(
                    {
                        "user": name,
                        "action": "create_secret_disclosure",
                        "secret": plain,
                    }
                )
                secret_name = "iam-access-key-%s" % (name or uid)
                try:
                    secret.save_secret(
                        iam.get_credentials(None), cfg, secret_name, plain
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("凭据入库失败（可忽略）：%s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.error("为用户 %s 创建密钥失败：%s", name, exc)

    # 2) 对每把现有密钥执行禁用/删除
    for x in key_info:
        act = iam.decide_key_action(x["age"], x["status"], cfg)
        if act == "delete":
            try:
                iam.delete_access_key(client, x["access"])
                actions.append(
                    {"user": name, "action": "delete", "access": x["access"]}
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("删除密钥 %s 失败：%s", x["access"], exc)
        elif act == "disable":
            try:
                iam.disable_access_key(client, x["access"])
                actions.append(
                    {"user": name, "action": "disable", "access": x["access"]}
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("禁用密钥 %s 失败：%s", x["access"], exc)

    return actions


def rotate_all(client, cfg):
    """遍历域下用户并执行轮转。"""
    domain_id = cfg.get("domain_id")
    if not domain_id:
        raise RuntimeError("缺少 DOMAIN_ID，无法列举用户")

    users = iam.list_domain_users(client, domain_id)
    all_actions = []
    for u in users:
        name = getattr(u, "name", None)
        if cfg.get("target_user_filter") and name != cfg["target_user_filter"]:
            continue
        all_actions.extend(rotate_one_user(client, cfg, u))

    return {"scanned_users": len(users), "actions": all_actions}


def format_report(result):
    """构造人类可读的通知正文。"""
    lines = ["IAM 访问密钥轮转结果", "=" * 24]
    lines.append("扫描用户数：%d" % result.get("scanned_users", 0))
    for a in result.get("actions", []):
        if a.get("action") == "create_secret_disclosure":
            lines.append("  [新建] 用户 %s 新密钥明文：%s" % (a.get("user"), a.get("secret")))
        else:
            lines.append("  [%s] 用户 %s 密钥 %s" % (a.get("action"), a.get("user"), a.get("access")))
    return "\n".join(lines)


def handler(event, context):
    print("=== HANDLER ENTRY ===", flush=True)
    cfg = config.get_config()
    creds = iam.get_credentials(context)
    client = iam.build_iam_client(cfg["region"], creds)

    result = rotate_all(client, cfg)

    if cfg.get("notify_topic_urn"):
        try:
            notify.publish(creds, cfg, "IAM 访问密钥轮转结果", format_report(result))
        except Exception as exc:  # noqa: BLE001
            logger.error("通知发布失败：%s", exc)

    return {
        "statusCode": 200,
        "body": json.dumps(result, ensure_ascii=False, default=str),
    }
