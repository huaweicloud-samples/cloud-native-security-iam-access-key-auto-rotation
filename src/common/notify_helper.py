"""消息通知服务（SMN）封装：向主题发布消息。"""

import logging

logger = logging.getLogger(__name__)


def build_client(region, creds):
    """构造 SMN 客户端。"""
    from huaweicloudsdksmn.v2 import SmnClient
    from huaweicloudsdksmn.v2.region.smn_region import SmnRegion

    return (
        SmnClient.new_builder()
        .with_credentials(creds)
        .with_region(SmnRegion.value_of(region))
        .build()
    )


def publish(creds, cfg, subject, message):
    """向配置的主题发布一条消息。

    creds 由调用方从执行上下文获取后传入；topic_urn 来自函数环境变量。
    """
    from huaweicloudsdksmn.v2 import PublishMessageRequest, PublishMessageRequestBody

    if not cfg.get("notify_topic_urn"):
        logger.warning("未配置通知主题 URN，跳过发布")
        return None

    client = build_client(cfg["region"], creds)
    body = PublishMessageRequestBody(subject=subject, message=message)
    req = PublishMessageRequest()
    req.topic_urn = cfg["notify_topic_urn"]
    req.body = body
    resp = client.publish_message(req)
    logger.info("通知已发布：%s", getattr(resp, "message_id", ""))
    return resp
