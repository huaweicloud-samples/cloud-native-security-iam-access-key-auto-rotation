#!/usr/bin/env bash
# ============================================================================
# 构建三个函数部署包（zip），输出到 infra/build/
# 依赖：python3, pip
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
STAGE="$BUILD_DIR/_stage"

PYTHON_BIN="${PYTHON_BIN:-python3}"

SDK_PKGS="huaweicloudsdkcore huaweicloudsdkiam huaweicloudsdksmn huaweicloudsdkcsms"

FUNCS=("rotate" "inventory" "notifier")

rm -rf "$STAGE" "$BUILD_DIR"/*.zip
mkdir -p "$STAGE"

echo "==> 安装 SDK 依赖（Linux x86_64 纯 Python 轮子）"
"$PYTHON_BIN" -m pip install --target "$STAGE" --platform manylinux2014_x86_64 --python-version 39 --only-binary=:all: $SDK_PKGS

for fn in "${FUNCS[@]}"; do
  echo "==> 打包函数：$fn"
  work="$BUILD_DIR/_$fn"
  rm -rf "$work"
  mkdir -p "$work"

  cp -r "$ROOT_DIR/src/common" "$work/common"
  cp "$ROOT_DIR/src/functions/$fn/index.py" "$work/index.py"

  # 复制 SDK 依赖（仅纯 Python 包，过滤原生扩展与元数据）
  cp -r "$STAGE"/* "$work/" 2>/dev/null || true

  # 清理非必要文件
  find "$work" -name "__pycache__" -type d -prune -exec rm -rf {} +
  find "$work" -name "*.dist-info" -type d -prune -exec rm -rf {} +
  find "$work" -name "*.egg-info" -type d -prune -exec rm -rf {} +

  (cd "$work" && zip -qr "$BUILD_DIR/$fn.zip" .)
  rm -rf "$work"
  echo "    生成：$BUILD_DIR/$fn.zip"
done

rm -rf "$STAGE"
echo "==> 完成，部署包位于 $BUILD_DIR"
