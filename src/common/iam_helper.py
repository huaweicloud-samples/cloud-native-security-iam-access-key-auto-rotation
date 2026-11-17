"""IAM 访问密钥生命周期操作与轮转决策。

说明：SDK 相关导入放在函数内部（懒加载），保证打包缺失依赖时不会在模块加载阶段静默崩溃；
纯决策函数（decide_key_action / should_create_new）不依赖任何 SDK，可在本地直接测试。
"""

import os
import datetime
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 纯决策逻辑（无 SDK 依赖，可被 selftest 直接调用）
# ---------------------------------------------------------------------------
def decide_key_action(age_days, status, cfg):
    """依据密钥年龄与状态返回建议动作。

    - 年龄 >= 删除周期 -> delete
    - 年龄 >= 禁用周期 且仍启用 -> disable
    - 年龄 >= 轮转周期 -> create（新建动作由调用方按用户维度去重）
    - 其余 -> none
    """
    if age_days >= cfg["delete_period_days"]:
        return "delete"
    if age_days >= cfg["inactive_period_days"]:
        return "disable" if status == "ACTIVE" else "none"
    if age_days >= cfg["rotation_period_days"]:
        return "create"
    return "none"


def should_create_new(newest_age_days, active_count, cfg):
    """是否应为该用户新建一把密钥。

    仅当最新密钥已到轮转周期、且当前活跃密钥不超过 1 把时新建，避免每天重复创建。
    """
    if newest_age_days >= cfg["rotation_period_days"] and active_count <= 1:
        return True
    return False


# ---------------------------------------------------------------------------
# 凭证与客户端
# ---------------------------------------------------------------------------
def get_credentials(context):
    """从函数执行上下文注入的临时凭证构造 BasicCredentials。"""
    ak = sk = token = None
    if context is not None:
        try:
            ak = context.getSecurityAccessKey()
            sk = context.getSecuritySecretKey()
            token = context.getSecurityToken()
        except Exception:  # noqa: BLE001
            pass
    project_id = os.environ.get("HW_PROJECT_ID")
    from huaweicloudsdkcore.auth.credentials import BasicCredentials

    if not ak or not sk:
        raise RuntimeError("请确认函数已绑定执行委托")
    creds = BasicCredentials(ak, sk, project_id)
    if token:
        creds = creds.with_security_token(token)
    return creds


def build_iam_client(region, creds):
    """构造 IAM v3 客户端。"""
    from huaweicloudsdkiam.v3 import IamClient
    from huaweicloudsdkiam.v3.region.iam_region import IamRegion

    return (
        IamClient.new_builder()
        .with_credentials(creds)
        .with_region(IamRegion.value_of(region))
        .build()
    )


# ---------------------------------------------------------------------------
# IAM 操作封装
# ---------------------------------------------------------------------------
def list_domain_users(client, domain_id, name=None):
    """列举域下用户。"""
    from huaweicloudsdkiam.v3 import KeystoneListUsersRequest

    req = KeystoneListUsersRequest(domain_id=domain_id)
    if name:
        req.name = name
    resp = client.keystone_list_users(req)
    return getattr(resp, "users", None) or []


def list_user_access_keys(client, user_id):
    """列举指定用户的访问密钥。"""
    from huaweicloudsdkiam.v3 import ListPermanentAccessKeysRequest

    req = ListPermanentAccessKeysRequest(user_id=user_id)
    resp = client.list_permanent_access_keys(req)
    return getattr(resp, "credentials", None) or []


def create_access_key(client, user_id, description="auto-rotated"):
    """为指定用户创建新的访问密钥，返回含明文的凭据对象。"""
    from huaweicloudsdkiam.v3 import (
        CreatePermanentAccessKeyRequest,
        CreatePermanentAccessKeyRequestBody,
        CreateCredentialOption,
    )

    body = CreatePermanentAccessKeyRequestBody(
        credential=CreateCredentialOption(user_id=user_id, description=description)
    )
    req = CreatePermanentAccessKeyRequest(body=body)
    resp = client.create_permanent_access_key(req)
    return resp.credential


def disable_access_key(client, access_key):
    """将指定访问密钥置为禁用。"""
    from huaweicloudsdkiam.v3 import (
        UpdatePermanentAccessKeyRequest,
        UpdatePermanentAccessKeyRequestBody,
        UpdateCredentialOption,
    )

    body = UpdatePermanentAccessKeyRequestBody(
        credential=UpdateCredentialOption(status="INACTIVE")
    )
    req = UpdatePermanentAccessKeyRequest(access_key=access_key, body=body)
    client.update_permanent_access_key(req)


def delete_access_key(client, access_key):
    """删除指定访问密钥。"""
    from huaweicloudsdkiam.v3 import DeletePermanentAccessKeyRequest

    req = DeletePermanentAccessKeyRequest(access_key=access_key)
    client.delete_permanent_access_key(req)


# ---------------------------------------------------------------------------
# 时间解析辅助
# ---------------------------------------------------------------------------
def parse_create_time(value):
    """将 IAM 返回的时间字符串解析为带时区的 datetime；失败返回 None。"""
    if not value:
        return None
    candidate = value.replace("Z", "+00:00")
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.datetime.fromisoformat(candidate)
    except ValueError:
        return None
