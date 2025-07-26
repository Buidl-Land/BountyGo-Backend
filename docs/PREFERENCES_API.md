# 用户偏好管理 API 文档

## 概述

用户偏好管理API提供了个性化设置和智能推荐功能，帮助用户：

- 管理个人偏好设置
- 获取智能化的偏好建议
- 优化任务推荐效果
- 自定义系统行为

## 基础信息

- **基础URL**: `/api/v1/multi-agent/preferences`
- **认证方式**: Bearer Token (JWT)
- **内容类型**: `application/json`

## 偏好设置项说明

### 输出格式 (output_format)

控制系统响应的详细程度：

- `concise` - 简洁模式，只返回核心信息
- `detailed` - 详细模式，包含完整分析结果
- `structured` - 结构化模式，按类别组织信息

### 语言偏好 (language)

支持的语言代码：

- `zh-CN` - 简体中文
- `en-US` - 美式英语
- `ja-JP` - 日语
- `ko-KR` - 韩语

### 分析重点 (analysis_focus)

可选的分析维度：

- `technical_requirements` - 技术要求分析
- `reward_analysis` - 奖励分析
- `deadline_analysis` - 截止日期分析
- `difficulty_assessment` - 难度评估
- `skill_matching` - 技能匹配
- `market_trends` - 市场趋势

### 质量阈值 (quality_threshold)

任务质量评分阈值 (0.0-1.0)：

- `0.9-1.0` - 仅显示高质量任务
- `0.7-0.9` - 中高质量任务
- `0.5-0.7` - 中等质量任务
- `0.0-0.5` - 所有质量任务

### 自动创建任务 (auto_create_tasks)

- `true` - 分析后自动创建任务到数据库
- `false` - 仅分析不创建任务

## API端点详解

### 1. 获取用户偏好

**GET** `/api/v1/multi-agent/preferences`

获取当前用户的完整偏好设置。

#### 响应示例

```json
{
  "user_id": "user_12345",
  "output_format": "detailed",
  "language": "zh-CN",
  "analysis_focus": [
    "technical_requirements",
    "reward_analysis",
    "skill_matching"
  ],
  "quality_threshold": 0.8,
  "auto_create_tasks": true,
  "task_types": ["programming", "web3", "design"],
  "notification_preferences": {
    "email_enabled": true,
    "push_enabled": false,
    "frequency": "daily"
  },
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### 使用示例

```bash
curl -X GET "http://localhost:8000/api/v1/multi-agent/preferences" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. 更新用户偏好

**PUT** `/api/v1/multi-agent/preferences`

更新用户的偏好设置，支持部分更新。

#### 请求参数

```json
{
  "output_format": "concise",
  "language": "en-US",
  "analysis_focus": ["reward_analysis", "deadline_analysis"],
  "quality_threshold": 0.9,
  "auto_create_tasks": false,
  "task_types": ["programming", "data-science"],
  "notification_preferences": {
    "email_enabled": false,
    "push_enabled": true,
    "frequency": "weekly"
  }
}
```

#### 响应示例

```json
{
  "user_id": "user_12345",
  "output_format": "concise",
  "language": "en-US",
  "analysis_focus": ["reward_analysis", "deadline_analysis"],
  "quality_threshold": 0.9,
  "auto_create_tasks": false,
  "task_types": ["programming", "data-science"],
  "notification_preferences": {
    "email_enabled": false,
    "push_enabled": true,
    "frequency": "weekly"
  },
  "updated_at": "2024-01-15T11:45:00Z"
}
```

#### 使用示例

```bash
curl -X PUT "http://localhost:8000/api/v1/multi-agent/preferences" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "output_format": "detailed",
    "quality_threshold": 0.85,
    "auto_create_tasks": true
  }'
```

### 3. 获取偏好建议

**GET** `/api/v1/multi-agent/preferences/suggestions`

基于用户历史行为和系统分析，获取个性化的偏好优化建议。

#### 响应示例

```json
{
  "suggestions": [
    {
      "preference_key": "analysis_focus",
      "suggested_value": ["technical_requirements", "difficulty_assessment"],
      "reason": "基于您最近选择的任务类型，建议关注技术要求和难度评估",
      "confidence": 0.87,
      "impact_description": "这将帮助您更好地评估任务的技术挑战",
      "data_source": "recent_task_selections"
    },
    {
      "preference_key": "quality_threshold",
      "suggested_value": 0.85,
      "reason": "您通常选择高质量任务，建议提高质量阈值",
      "confidence": 0.92,
      "impact_description": "过滤掉低质量任务，节省您的时间",
      "data_source": "task_completion_history"
    },
    {
      "preference_key": "task_types",
      "suggested_value": ["programming", "web3", "blockchain"],
      "reason": "检测到您对区块链技术的兴趣增加",
      "confidence": 0.78,
      "impact_description": "将为您推荐更多相关的高价值任务",
      "data_source": "search_history_analysis"
    }
  ],
  "generated_at": "2024-01-15T12:00:00Z",
  "next_suggestion_time": "2024-01-22T12:00:00Z"
}
```

#### 查询参数

- `category` (可选): 指定建议类别 (`output`, `analysis`, `quality`, `tasks`)
- `limit` (可选): 限制建议数量，默认为5

#### 使用示例

```bash
curl -X GET "http://localhost:8000/api/v1/multi-agent/preferences/suggestions?category=analysis&limit=3" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. 应用偏好建议

**POST** `/api/v1/multi-agent/preferences/apply-suggestion`

应用系统推荐的偏好建议。

#### 请求参数

```json
{
  "suggestion_id": "suggestion_12345",
  "apply": true,
  "feedback": "这个建议很有用，提高了我的任务匹配度"
}
```

#### 响应示例

```json
{
  "success": true,
  "applied_changes": {
    "analysis_focus": ["technical_requirements", "difficulty_assessment"]
  },
  "message": "偏好建议已成功应用",
  "updated_preferences": {
    "user_id": "user_12345",
    "analysis_focus": ["technical_requirements", "difficulty_assessment"],
    "updated_at": "2024-01-15T12:15:00Z"
  }
}
```

### 5. 偏好历史记录

**GET** `/api/v1/multi-agent/preferences/history`

获取用户偏好的变更历史。

#### 查询参数

- `limit` (可选): 限制返回记录数，默认为20
- `start_date` (可选): 开始日期 (ISO 8601格式)
- `end_date` (可选): 结束日期 (ISO 8601格式)

#### 响应示例

```json
{
  "history": [
    {
      "change_id": "change_001",
      "timestamp": "2024-01-15T12:15:00Z",
      "change_type": "manual_update",
      "changed_fields": ["analysis_focus", "quality_threshold"],
      "old_values": {
        "analysis_focus": ["reward_analysis"],
        "quality_threshold": 0.7
      },
      "new_values": {
        "analysis_focus": ["technical_requirements", "difficulty_assessment"],
        "quality_threshold": 0.85
      },
      "trigger": "user_action",
      "impact_score": 0.8
    },
    {
      "change_id": "change_002",
      "timestamp": "2024-01-10T09:30:00Z",
      "change_type": "suggestion_applied",
      "changed_fields": ["task_types"],
      "old_values": {
        "task_types": ["programming"]
      },
      "new_values": {
        "task_types": ["programming", "web3"]
      },
      "trigger": "system_suggestion",
      "suggestion_id": "suggestion_12344",
      "impact_score": 0.9
    }
  ],
  "total_count": 15,
  "has_more": true
}
```

### 6. 重置偏好设置

**POST** `/api/v1/multi-agent/preferences/reset`

将用户偏好重置为系统默认值或指定配置。

#### 请求参数

```json
{
  "reset_type": "default",  // "default" | "recommended" | "custom"
  "custom_config": {        // 仅当 reset_type 为 "custom" 时需要
    "output_format": "detailed",
    "language": "zh-CN",
    "quality_threshold": 0.8
  },
  "confirm": true
}
```

#### 响应示例

```json
{
  "success": true,
  "message": "偏好设置已重置为默认配置",
  "reset_preferences": {
    "user_id": "user_12345",
    "output_format": "detailed",
    "language": "zh-CN",
    "analysis_focus": ["technical_requirements", "reward_analysis"],
    "quality_threshold": 0.8,
    "auto_create_tasks": true,
    "updated_at": "2024-01-15T13:00:00Z"
  },
  "backup_created": true,
  "backup_id": "backup_20240115_130000"
}
```

## 偏好影响说明

### 对任务推荐的影响

不同偏好设置如何影响推荐结果：

| 偏好设置 | 影响描述 | 示例 |
|---------|---------|------|
| `quality_threshold: 0.9` | 只推荐高质量任务 | 过滤掉描述不清晰的任务 |
| `analysis_focus: ["reward_analysis"]` | 重点分析奖励信息 | 详细展示薪资结构和支付方式 |
| `task_types: ["web3"]` | 优先推荐Web3任务 | 区块链、DeFi、NFT相关任务 |
| `language: "zh-CN"` | 中文界面和分析 | 所有响应使用中文 |

### 对系统行为的影响

| 偏好设置 | 系统行为变化 |
|---------|-------------|
| `auto_create_tasks: true` | 分析URL后自动创建任务 |
| `output_format: "concise"` | 返回简化的分析结果 |
| `notification_preferences` | 控制通知频率和方式 |

## 最佳实践

### 1. 偏好设置策略

```python
# 新用户推荐配置
new_user_config = {
    "output_format": "detailed",      # 详细信息帮助学习
    "quality_threshold": 0.7,         # 较低阈值看到更多选择
    "auto_create_tasks": false,       # 手动控制任务创建
    "analysis_focus": ["technical_requirements", "reward_analysis"]
}

# 经验用户推荐配置
experienced_user_config = {
    "output_format": "concise",       # 简洁信息提高效率
    "quality_threshold": 0.9,         # 高质量任务节省时间
    "auto_create_tasks": true,        # 自动化工作流程
    "analysis_focus": ["skill_matching", "market_trends"]
}
```

### 2. 动态偏好调整

```python
# 根据用户行为动态调整
def adjust_preferences_based_on_behavior(user_behavior):
    adjustments = {}
    
    # 如果用户经常选择高奖励任务
    if user_behavior.avg_selected_reward > 1000:
        adjustments["analysis_focus"] = ["reward_analysis", "market_trends"]
    
    # 如果用户技能水平提升
    if user_behavior.completed_difficult_tasks > 5:
        adjustments["quality_threshold"] = min(0.9, current_threshold + 0.1)
    
    return adjustments
```

### 3. 偏好验证

```python
def validate_preferences(preferences):
    """验证偏好设置的合理性"""
    issues = []
    
    # 检查质量阈值是否过高
    if preferences.quality_threshold > 0.95:
        issues.append("质量阈值过高可能导致推荐任务过少")
    
    # 检查分析重点是否过多
    if len(preferences.analysis_focus) > 4:
        issues.append("分析重点过多可能影响响应速度")
    
    return issues
```

## 集成示例

### JavaScript 客户端

```javascript
class PreferencesManager {
  constructor(apiClient) {
    this.api = apiClient;
  }

  async getPreferences() {
    return await this.api.get('/preferences');
  }

  async updatePreferences(updates) {
    return await this.api.put('/preferences', updates);
  }

  async getSuggestions(category = null) {
    const params = category ? { category } : {};
    return await this.api.get('/preferences/suggestions', { params });
  }

  async applySuggestion(suggestionId, feedback = null) {
    return await this.api.post('/preferences/apply-suggestion', {
      suggestion_id: suggestionId,
      apply: true,
      feedback
    });
  }

  // 智能偏好更新
  async smartUpdate(userBehavior) {
    const suggestions = await this.getSuggestions();
    const relevantSuggestions = suggestions.suggestions.filter(
      s => s.confidence > 0.8
    );

    for (const suggestion of relevantSuggestions) {
      if (this.shouldApplySuggestion(suggestion, userBehavior)) {
        await this.applySuggestion(suggestion.suggestion_id);
      }
    }
  }

  shouldApplySuggestion(suggestion, userBehavior) {
    // 基于用户行为决定是否应用建议
    switch (suggestion.preference_key) {
      case 'quality_threshold':
        return userBehavior.taskCompletionRate > 0.8;
      case 'task_types':
        return userBehavior.recentSearches.includes(suggestion.suggested_value[0]);
      default:
        return suggestion.confidence > 0.85;
    }
  }
}

// 使用示例
const prefsManager = new PreferencesManager(apiClient);

// 获取并显示当前偏好
const currentPrefs = await prefsManager.getPreferences();
console.log('当前偏好:', currentPrefs);

// 更新偏好
await prefsManager.updatePreferences({
  quality_threshold: 0.85,
  analysis_focus: ['technical_requirements', 'reward_analysis']
});

// 获取并应用建议
const suggestions = await prefsManager.getSuggestions('analysis');
if (suggestions.suggestions.length > 0) {
  await prefsManager.applySuggestion(
    suggestions.suggestions[0].suggestion_id,
    '这个建议很有帮助'
  );
}
```

### Python 客户端

```python
from typing import Dict, List, Optional
import requests

class PreferencesClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = f"{base_url}/preferences"
        self.headers = {"Authorization": f"Bearer {token}"}

    def get_preferences(self) -> Dict:
        """获取用户偏好"""
        response = requests.get(self.base_url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def update_preferences(self, updates: Dict) -> Dict:
        """更新用户偏好"""
        response = requests.put(
            self.base_url,
            json=updates,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_suggestions(self, category: Optional[str] = None) -> Dict:
        """获取偏好建议"""
        params = {"category": category} if category else {}
        response = requests.get(
            f"{self.base_url}/suggestions",
            params=params,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def apply_suggestion(self, suggestion_id: str, feedback: Optional[str] = None) -> Dict:
        """应用偏好建议"""
        data = {
            "suggestion_id": suggestion_id,
            "apply": True,
            "feedback": feedback
        }
        response = requests.post(
            f"{self.base_url}/apply-suggestion",
            json=data,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_history(self, limit: int = 20) -> Dict:
        """获取偏好历史"""
        response = requests.get(
            f"{self.base_url}/history",
            params={"limit": limit},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def reset_preferences(self, reset_type: str = "default") -> Dict:
        """重置偏好设置"""
        data = {"reset_type": reset_type, "confirm": True}
        response = requests.post(
            f"{self.base_url}/reset",
            json=data,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# 使用示例
client = PreferencesClient("http://localhost:8000/api/v1/multi-agent", "your-token")

# 获取当前偏好
prefs = client.get_preferences()
print(f"当前语言: {prefs['language']}")
print(f"质量阈值: {prefs['quality_threshold']}")

# 更新偏好
updated_prefs = client.update_preferences({
    "output_format": "detailed",
    "analysis_focus": ["technical_requirements", "skill_matching"],
    "quality_threshold": 0.85
})

# 获取建议并应用
suggestions = client.get_suggestions("quality")
if suggestions["suggestions"]:
    best_suggestion = max(
        suggestions["suggestions"],
        key=lambda x: x["confidence"]
    )
    
    result = client.apply_suggestion(
        best_suggestion["suggestion_id"],
        "系统建议很准确"
    )
    print(f"已应用建议: {result['message']}")
```

## 错误处理

### 常见错误

```json
{
  "detail": "Invalid preference value",
  "error_code": "INVALID_PREFERENCE_VALUE",
  "field": "quality_threshold",
  "valid_range": "0.0 - 1.0",
  "provided_value": 1.5
}
```

### 错误码说明

- `INVALID_PREFERENCE_VALUE` - 偏好值无效
- `PREFERENCE_NOT_FOUND` - 偏好项不存在
- `SUGGESTION_EXPIRED` - 建议已过期
- `RESET_CONFIRMATION_REQUIRED` - 需要确认重置操作

## 更新日志

### v1.0.0 (2024-01-15)
- 初始版本发布
- 基础偏好管理功能
- 智能建议系统
- 偏好历史记录

### 未来计划
- A/B测试偏好配置
- 机器学习优化建议算法
- 团队偏好管理
- 更多个性化选项