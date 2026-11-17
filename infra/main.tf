# ============================================================================
# 华为云 IAM 访问密钥自动轮转 — Terraform 主入口
# 资源：函数执行委托 / 对象存储桶 / 消息通知主题 / 三个函数 / 三个定时触发器
# ============================================================================

terraform {
  required_version = ">= 1.5"

  required_providers {
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = ">= 1.97.0"
    }
  }
}

provider "huaweicloud" {
  region = var.region
  # AK/SK 从环境变量读取，不硬编码：
  # export HW_ACCESS_KEY="<AK>"
  # export HW_SECRET_KEY="<SK>"
}

# 用于创建「云服务委托」的别名 Provider：
# 创建 FunctionGraph 云服务委托必须走全局 IAM 端点（区域端点无法解析服务名）。
provider "huaweicloud" {
  alias  = "global_iam"
  region = var.region
  endpoints = {
    iam = "https://iam.myhuaweicloud.com"
  }
}

# 当前账号（域）信息，用于函数列举用户
data "huaweicloud_account" "current" {}

# ----------------------------------------------------------------------------
# 委托：函数执行时经此获取临时凭证调用 IAM / SMN / OBS / CSMS
# ----------------------------------------------------------------------------
resource "huaweicloud_identity_agency" "fgs" {
  # 当凭据不具备 iam:agencies:create / get 权限时，设为 false 并改为引用
  # 控制台已创建好的同名委托（此时 Terraform 不再读写该委托）。
  count                  = var.manage_agency ? 1 : 0
  provider               = huaweicloud.global_iam
  name                   = var.agency_name
  description            = "Agency for IAM key rotation functions"
  duration               = "FOREVER"
  delegated_service_name = "functiongraph"

  project_role {
    project = var.region
    roles = [
      "IAM Administrator",
      "SMN FullAccess",
      "DEW FullAccess",
      "KMS Administrator",
    ]
  }

  domain_roles = [
    "OBS Administrator",
  ]
}

# ----------------------------------------------------------------------------
# 对象存储：托管三个函数部署包
# ----------------------------------------------------------------------------
resource "huaweicloud_obs_bucket" "assets" {
  bucket        = var.obs_bucket_name
  acl           = "private"
  force_destroy = true
}

resource "huaweicloud_obs_bucket_object" "rotate" {
  bucket       = huaweicloud_obs_bucket.assets.bucket
  key          = "build/rotate.zip"
  source       = "${path.module}/build/rotate.zip"
  content_type = "application/zip"
}

resource "huaweicloud_obs_bucket_object" "inventory" {
  bucket       = huaweicloud_obs_bucket.assets.bucket
  key          = "build/inventory.zip"
  source       = "${path.module}/build/inventory.zip"
  content_type = "application/zip"
}

resource "huaweicloud_obs_bucket_object" "notifier" {
  bucket       = huaweicloud_obs_bucket.assets.bucket
  key          = "build/notifier.zip"
  source       = "${path.module}/build/notifier.zip"
  content_type = "application/zip"
}

# ----------------------------------------------------------------------------
# 消息通知：轮转事件推送主题 + 邮件订阅
# ----------------------------------------------------------------------------
resource "huaweicloud_smn_topic" "notify" {
  name         = var.smn_topic_name
  display_name = "IAM Key Rotation"
}

resource "huaweicloud_smn_subscription" "email" {
  topic_urn = huaweicloud_smn_topic.notify.topic_urn
  protocol  = "email"
  endpoint  = var.email_subscription
}

# ----------------------------------------------------------------------------
# 公共函数环境变量
# ----------------------------------------------------------------------------
locals {
  # 委托名：自建时取资源名，否则直接取变量（引用控制台已建好的委托）
  agency_name = var.manage_agency ? huaweicloud_identity_agency.fgs[0].name : var.agency_name

  common_env = {
    REGION               = var.region
    DOMAIN_ID            = data.huaweicloud_account.current.id
    OBS_BUCKET           = huaweicloud_obs_bucket.assets.bucket
    NOTIFY_TOPIC_URN     = huaweicloud_smn_topic.notify.topic_urn
    ROTATION_PERIOD_DAYS = tostring(var.rotation_period_days)
    INACTIVE_PERIOD_DAYS = tostring(var.inactive_period_days)
    DELETE_PERIOD_DAYS   = tostring(var.delete_period_days)
    TARGET_USER_FILTER   = var.target_user_filter
  }
}

# ----------------------------------------------------------------------------
# 轮转函数 rotate
# ----------------------------------------------------------------------------
resource "huaweicloud_fgs_function" "rotate" {
  name        = "${var.project_name}-rotate"
  app         = "iamkeyrotation"
  agency      = local.agency_name
  handler     = "index.handler"
  memory_size = var.function_memory
  timeout     = var.function_timeout
  runtime     = "Python3.9"
  code_type   = "obs"
  code_url    = "https://${huaweicloud_obs_bucket.assets.bucket}.obs.${var.region}.myhuaweicloud.com/build/rotate.zip"

  user_data = jsonencode(local.common_env)

  lifecycle {
    ignore_changes = [code_url]
  }
}

resource "huaweicloud_fgs_function_trigger" "rotate_timer" {
  function_urn = huaweicloud_fgs_function.rotate.urn
  type         = "TIMER"
  status       = "ACTIVE"
  event_data   = jsonencode({
    name          = "rotate-timer"
    schedule_type = "Cron"
    schedule      = "0 0 0 * * ?"
    user_event    = ""
  })

  lifecycle {
    ignore_changes = [event_data, status]
  }
}

# ----------------------------------------------------------------------------
# 清单函数 inventory
# ----------------------------------------------------------------------------
resource "huaweicloud_fgs_function" "inventory" {
  name        = "${var.project_name}-inventory"
  app         = "iamkeyrotation"
  agency      = local.agency_name
  handler     = "index.handler"
  memory_size = var.function_memory
  timeout     = var.function_timeout
  runtime     = "Python3.9"
  code_type   = "obs"
  code_url    = "https://${huaweicloud_obs_bucket.assets.bucket}.obs.${var.region}.myhuaweicloud.com/build/inventory.zip"

  user_data = jsonencode(local.common_env)

  lifecycle {
    ignore_changes = [code_url]
  }
}

resource "huaweicloud_fgs_function_trigger" "inventory_timer" {
  function_urn = huaweicloud_fgs_function.inventory.urn
  type         = "TIMER"
  status       = "ACTIVE"
  event_data   = jsonencode({
    name          = "inventory-timer"
    schedule_type = "Cron"
    schedule      = "0 30 0 * * ?"
    user_event    = ""
  })

  lifecycle {
    ignore_changes = [event_data, status]
  }
}

# ----------------------------------------------------------------------------
# 通知函数 notifier
# ----------------------------------------------------------------------------
resource "huaweicloud_fgs_function" "notifier" {
  name        = "${var.project_name}-notifier"
  app         = "iamkeyrotation"
  agency      = local.agency_name
  handler     = "index.handler"
  memory_size = var.function_memory
  timeout     = var.function_timeout
  runtime     = "Python3.9"
  code_type   = "obs"
  code_url    = "https://${huaweicloud_obs_bucket.assets.bucket}.obs.${var.region}.myhuaweicloud.com/build/notifier.zip"

  user_data = jsonencode(local.common_env)

  lifecycle {
    ignore_changes = [code_url]
  }
}

# ----------------------------------------------------------------------------
# 输出
# ----------------------------------------------------------------------------
output "rotate_function_urn" {
  description = "轮转函数 URN"
  value       = huaweicloud_fgs_function.rotate.urn
}

output "inventory_function_urn" {
  description = "清单函数 URN"
  value       = huaweicloud_fgs_function.inventory.urn
}

output "notifier_function_urn" {
  description = "通知函数 URN"
  value       = huaweicloud_fgs_function.notifier.urn
}

output "smn_topic_urn" {
  description = "消息通知主题 URN"
  value       = huaweicloud_smn_topic.notify.topic_urn
}

output "obs_bucket" {
  description = "对象存储桶名"
  value       = huaweicloud_obs_bucket.assets.bucket
}
