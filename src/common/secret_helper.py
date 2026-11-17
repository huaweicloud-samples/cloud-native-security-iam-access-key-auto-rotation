"""凭据管理服务（CSMS）封装：保存最新密钥明文。

说明：当前版本的更新接口不接收明文值，因此「保存」采用「先删后建」的方式，
保证每次轮转后凭据中存放的是最新一把密钥的明文。
"""

import logging

logger = logging.getLogger(__name__)


def build_client(region, creds):
    """构造 CSMS 客户端。"""
    from huaweicloudsdkcsms.v1 import CsmsClient
    from huaweicloudsdkcsms.v1.region.csms_region import CsmsRegion

    return (
        CsmsClient.new_builder()
        .with_credentials(creds)
        .with_region(CsmsRegion.value_of(region))
        .build()
    )


def save_secret(creds, cfg, name, secret_string):
    """将最新密钥明文存入凭据；若已存在则重建。"""
    from huaweicloudsdkcsms.v1 import (
        CreateSecretRequest,
        CreateSecretRequestBody,
        DeleteSecretRequest,
    )

    client = build_client(cfg["region"], creds)
    try:
        client.delete_secret(DeleteSecretRequest(secret_name=name))
    except Exception:  # noqa: BLE001
        # 凭据不存在属正常情况
        pass

    body = CreateSecretRequestBody(
        name=name,
        secret_string=secret_string,
        description="IAM 访问密钥轮转保管",
    )
    client.create_secret(CreateSecretRequest(body=body))
    logger.info("凭据已保存：%s", name)
