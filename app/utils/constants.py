PROBLEM_TYPES = [
    "卫生问题",
    "设施故障",
    "服务态度",
    "噪音干扰",
    "价格问题",
    "安全问题",
    "交通不便",
    "早餐质量",
    "房间异味",
    "床上用品",
    "其他"
]

RESPONSIBILITY_TYPES = [
    "前台服务",
    "客房清洁",
    "工程维修",
    "餐饮服务",
    "安保部门",
    "管理层",
    "第三方合作",
    "不可抗力"
]

REVIEW_SOURCES = [
    "携程",
    "美团",
    "飞猪",
    "去哪儿",
    "Booking",
    "Airbnb",
    "到店投诉",
    "电话投诉",
    "其他"
]

RECTIFICATION_STATUSES = [
    "待整改",
    "整改中",
    "已完成"
]

TOPIC_STATUSES = [
    "进行中",
    "已关闭"
]

SUMMARY_MIN_LENGTH = 12
CONSECUTIVE_SAME_PROBLEM_THRESHOLD = 3

OVERDUE_DAYS = 7
LONG_TERM_RECTIFICATION_DAYS = 15

WARNING_TYPES = [
    "超期未整改",
    "长期整改中",
    "已完成但未复查"
]

WARNING_TYPE_COLORS = {
    "超期未整改": "#e74c3c",
    "长期整改中": "#f39c12",
    "已完成但未复查": "#9b59b6"
}
