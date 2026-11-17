# 部署指南 / Deployment Guide

本文件给出从零部署本实践的完整步骤。所有命令均使用相对路径，访问密钥通过环境变量传入部署脚本。

## 1. 准备工作

- 已安装 Terraform（`>= 1.5.0`）与 Python（`>= 3.9`）；
- 已创建华为云访问密钥，并导出环境变量：
  ```bash
  export HW_ACCESS_KEY="<your-access-key>"
  export HW_SECRET_KEY="<your-secret-key>"
  ```
- 已配置默认区域（如 `cn-north-4`）。

## 2. 构建函数部署包

每个函数需将源码、`common/` 公共模块与 `huaweicloudsdk*` 依赖打包为 zip。推荐使用与目标运行时（Python 3.9 / Linux x86_64）一致的纯 Python 轮子：

```bash
# 在仓库根目录执行
bash infra/build.sh
```

该脚本会：

1. 在隔离目录安装 `huaweicloudsdkcore`、`huaweicloudsdkiam`、`huaweicloudsdksmn`、`huaweicloudsdkcsms` 及其纯 Python 依赖；
2. 复制 `src/common/` 与对应 `src/functions/<name>/index.py`；
3. 过滤 `__pycache__`、`*.dist-info` 等非必要文件；
4. 输出 `rotate.zip`、`inventory.zip`、`notifier.zip` 到 `infra/build/`。

> 若使用本地打包机为其他平台，请强制拉取 Linux x86_64 纯 Python 轮子，避免原生扩展导致运行时加载失败。

## 3. 配置变量

复制示例文件并填入实际取值：

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# 编辑 terraform.tfvars，设置 project_name / domain_name / region / 邮箱订阅 等
```

## 4. 部署

```bash
cd infra
terraform init
terraform plan
terraform apply -auto-approve
```

完成后记录 `terraform output` 输出的函数 URN、SMN 主题 URN 与 OBS 桶名。

## 5. 订阅通知邮件

在消息通知服务控制台，为主题添加邮件协议订阅，并完成订阅确认。只有「已确认」的订阅才会收到轮转通知。

## 6. 验证

- 静态校验：`python -m py_compile src/common/*.py src/functions/*/index.py`
- 逻辑演练：`python src/functions/rotate/selftest.py`
- 语法校验：`terraform -chdir=infra validate`
- 云端：手动触发轮转函数，确认订阅邮箱收到通知，且 IAM 用户密钥按策略变更。

## 7. 清理

```bash
cd infra
terraform destroy -auto-approve
```

释放后，对象存储服务中如有额外手工上传对象，请一并清理。
