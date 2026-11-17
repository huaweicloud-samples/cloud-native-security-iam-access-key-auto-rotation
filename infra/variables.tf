variable "region" {
  description = "华为云区域"
  type        = string
  default     = "cn-north-4"
}

variable "project_name" {
  description = "项目名称，用于资源命名前缀"
  type        = string
  default     = "iam-key-rotation"
}

variable "domain_name" {
  description = "华为云账号域名（委托归属域），需替换为实际域名"
  type        = string
  default     = "your-huaweicloud-domain"
}

variable "obs_bucket_name" {
  description = "对象存储桶名（全局唯一）"
  type        = string
  default     = "iam-key-rotation-assets"
}

variable "agency_name" {
  description = "函数执行委托名称"
  type        = string
  default     = "iam-key-rotation-agency"
}

variable "manage_agency" {
  description = "是否由 Terraform 创建并托管执行委托。置 false 表示引用已在控制台创建好的同名委托（适用于凭据无 iam:agencies 权限的场景）"
  type        = bool
  default     = true
}

variable "smn_topic_name" {
  description = "消息通知主题名称"
  type        = string
  default     = "iam-key-rotation-topic"
}

variable "email_subscription" {
  description = "轮转通知的邮件订阅地址"
  type        = string
  default     = "ops@example.com"
}

variable "function_memory" {
  description = "函数内存规格（MB）"
  type        = number
  default     = 256
}

variable "function_timeout" {
  description = "函数超时时间（秒）"
  type        = number
  default     = 60
}

variable "rotation_period_days" {
  description = "触发新建访问密钥的天数阈值"
  type        = number
  default     = 90
}

variable "inactive_period_days" {
  description = "触发禁用旧访问密钥的天数阈值"
  type        = number
  default     = 100
}

variable "delete_period_days" {
  description = "触发删除旧访问密钥的天数阈值"
  type        = number
  default     = 110
}

variable "target_user_filter" {
  description = "仅对匹配该用户名的密钥轮转；为空表示全部用户"
  type        = string
  default     = ""
}
