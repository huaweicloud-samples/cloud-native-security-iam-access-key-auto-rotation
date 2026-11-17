"""轮转决策逻辑的离线测试（无需 SDK / 云端凭据）。

运行：python src/functions/rotate/selftest.py
"""

import os
import sys

# 将 src/ 加入搜索路径，便于直接导入 common 包
SRC_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, SRC_ROOT)

from common import iam_helper as iam  # noqa: E402


def test_decide_key_action():
    cfg = {
        "rotation_period_days": 90,
        "inactive_period_days": 100,
        "delete_period_days": 110,
    }
    assert iam.decide_key_action(120, "ACTIVE", cfg) == "delete"
    assert iam.decide_key_action(105, "ACTIVE", cfg) == "disable"
    assert iam.decide_key_action(95, "ACTIVE", cfg) == "create"
    # 已禁用且未到删除周期的密钥：保持不变
    assert iam.decide_key_action(105, "INACTIVE", cfg) == "none"
    # 未到期：保持不变
    assert iam.decide_key_action(50, "ACTIVE", cfg) == "none"
    print("OK  密钥动作决策")


def test_should_create_new():
    cfg = {
        "rotation_period_days": 90,
        "inactive_period_days": 100,
        "delete_period_days": 110,
    }
    assert iam.should_create_new(95, 1, cfg) is True
    # 已有两把活跃密钥时不重复创建
    assert iam.should_create_new(95, 2, cfg) is False
    # 未到轮转周期不创建
    assert iam.should_create_new(50, 1, cfg) is False
    print("OK  新建判定")


if __name__ == "__main__":
    test_decide_key_action()
    test_should_create_new()
    print("全部用例通过")
