region               = "cn-north-4"
project_name         = "iam-key-rotation"
domain_name          = "hid_n68mk7t2_1mc922"
obs_bucket_name      = "iam-key-rotation-assets-20260918"
agency_name          = "iam-key-rotaion-agency"
smn_topic_name       = "iam-key-rotation-topic"
email_subscription   = "verify-report-recipient@example.com"
function_memory      = 256
function_timeout     = 60
rotation_period_days = 90
inactive_period_days = 100
delete_period_days   = 110
target_user_filter   = "zz-no-real-user-zz"

# 复用控制台已创建并授权给函数工作流服务(op_svc_cff)的委托
manage_agency        = false
