# 智能推荐系统 API 文档

## 概述

智能推荐系统API基于RAG（检索增强生成）技术，为用户提供个性化的任务推荐服务：

- 基于用户技能和兴趣的智能匹配
- 自然语言查询推荐
- 实时推荐算法优化
- 用户反馈学习机制

## 基础信息

- **基础URL**: `/api/v1/multi-agent`
- **认证方式**: Bearer Token (JWT)
- **内容类型**: `application/json`

## 推荐算法说明

### 1. 用户画像构建

系统通过以下数据构建用户画像：

- **技能标签**: 从用户历史任务中提取
- **兴趣领域**: 基于搜索和浏览行为
- **偏好设置**: 用户主动设置的偏好
- **行为模式**: 任务选择和完成模式

### 2. 任务特征提取

对每个任务提取多维特征：

- **技术要求**: 所需技能和技术栈
- **难度等级**: 基于复杂度评估
- **奖励水平**: 薪资和激励结构
- **时间要求**: 截止日期和预估工时

### 3. 匹配算法

使用向量相似度和机器学习模型：

- **语义匹配**: 基于BERT/GPT的语义理解
- **协同过滤**: 相似用户的选择模式
- **内容过滤**: 基于任务内容特征
- **混合推荐**: 多种算法的加权组合

## API端点详解

### 1. 获取个性化推荐

**GET** `/api/v1/multi-agent/recommendations`

获取基于用户画像的个性化任务推荐。

#### 查询参数

- `limit` (可选): 推荐数量，默认10，最大50
- `category` (可选): 任务类别过滤 (`programming`, `design`, `web3`, `data-science`)
- `min_reward` (可选): 最低奖励金额
- `max_hours` (可选): 最大预估工时
- `difficulty` (可选): 难度等级 (`初级`, `中级`, `高级`)
- `refresh` (可选): 是否刷新推荐缓存，默认false

#### 响应示例

```json
{
  "recommendations": [
    {
      "task_id": 12345,
      "title": "DeFi协议智能合约开发",
      "description": "开发一个去中心化金融协议的智能合约，包括流动性挖矿和治理功能",
      "reward": 2500.0,
      "reward_currency": "USDT",
      "tags": ["solidity", "defi", "smart-contracts", "ethereum"],
      "difficulty_level": "高级",
      "estimated_hours": 80,
      "deadline": "2024-03-15T23:59:59Z",
      "match_score": 0.94,
      "match_reasons": [
        "完美匹配您的Solidity技能 (95%)",
        "符合您的Web3兴趣领域 (92%)",
        "奖励水平符合您的期望 (88%)",
        "项目复杂度适合您的经验 (90%)"
      ],
      "sponsor_info": {
        "name": "DeFi Protocol Labs",
        "rating": 4.8,
        "completed_projects": 23
      },
      "similar_tasks_completed": 3,
      "success_probability": 0.87
    },
    {
      "task_id": 12346,
      "title": "React Native移动应用开发",
      "description": "开发一个跨平台的加密货币钱包应用",
      "reward": 1800.0,
      "reward_currency": "USD",
      "tags": ["react-native", "mobile", "crypto", "wallet"],
      "difficulty_level": "中级",
      "estimated_hours": 60,
      "deadline": "2024-02-28T23:59:59Z",
      "match_score": 0.89,
      "match_reasons": [
        "匹配您的React技能 (85%)",
        "符合您的移动开发兴趣 (88%)",
        "适合您的时间安排 (92%)"
      ],
      "sponsor_info": {
        "name": "CryptoWallet Inc",
        "rating": 4.6,
        "completed_projects": 15
      },
      "similar_tasks_completed": 5,
      "success_probability": 0.91
    }
  ],
  "total_count": 2,
  "user_profile": {
    "skills": ["solidity", "javascript", "react", "python", "web3"],
    "interests": ["blockchain", "defi", "mobile-development", "fintech"],
    "experience_level": "高级",
    "preferred_reward_range": [1000, 3000],
    "availability_hours_per_week": 25,
    "preferences": {
      "output_format": "detailed",
      "language": "zh-CN",
      "analysis_focus": ["technical_requirements", "reward_analysis"],
      "task_types": ["programming", "web3"]
    }
  },
  "recommendation_metadata": {
    "algorithm_version": "v2.1",
    "generated_at": "2024-01-15T14:30:00Z",
    "cache_expires_at": "2024-01-15T15:30:00Z",
    "personalization_score": 0.92,
    "diversity_score": 0.78
  }
}
```

#### 使用示例

```bash
curl -X GET "http://localhost:8000/api/v1/multi-agent/recommendations?limit=5&category=web3&min_reward=1000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. 自然语言推荐查询

**POST** `/api/v1/multi-agent/ask-recommendations`

通过自然语言描述获取推荐，支持复杂查询条件。

#### 请求参数

```json
{
  "message": "我想找一些区块链相关的高薪任务，最好是Solidity开发，奖励在2000美元以上，工期不超过2个月"
}
```

#### 响应示例

```json
{
  "message": "根据您的要求，我为您找到了3个符合条件的区块链Solidity开发任务，奖励都在2000美元以上，工期在1-2个月之间。这些任务都非常适合您的技能水平。",
  "task_info": null,
  "suggestions": [
    "查看详细的任务推荐列表",
    "设置任务提醒",
    "更新您的技能档案以获得更精准推荐"
  ],
  "requires_action": true,
  "action_type": "show_recommendations",
  "processing_time": 2.1,
  "parsed_query": {
    "category": "blockchain",
    "skills": ["solidity"],
    "min_reward": 2000,
    "currency": "USD",
    "max_duration_months": 2,
    "priority": "high_reward"
  },
  "matched_tasks_count": 3,
  "recommendation_preview": [
    {
      "task_id": 12347,
      "title": "DeFi借贷协议开发",
      "reward": 2800.0,
      "match_score": 0.96
    },
    {
      "task_id": 12348,
      "title": "NFT市场智能合约",
      "reward": 2200.0,
      "match_score": 0.91
    }
  ]
}
```

#### 支持的查询类型

1. **技能导向查询**
   - "我想找Python相关的任务"
   - "有什么React开发的工作吗"

2. **奖励导向查询**
   - "找一些高薪的编程任务"
   - "奖励在1000-3000美元的任务"

3. **时间导向查询**
   - "这个月能完成的短期任务"
   - "长期项目，3个月以上的"

4. **领域导向查询**
   - "Web3和区块链相关的任务"
   - "AI和机器学习项目"

5. **复合查询**
   - "找一些Python Web3项目，奖励2000美元以上，工期1个月"

### 3. 更新用户档案

**POST** `/api/v1/multi-agent/update-user-profile`

更新用户的技能和兴趣档案，改善推荐效果。

#### 请求参数

```json
{
  "skills": [
    "solidity",
    "javascript",
    "python",
    "react",
    "node.js",
    "web3.js",
    "smart-contracts"
  ],
  "interests": [
    "blockchain",
    "defi",
    "nft",
    "dao",
    "fintech",
    "mobile-development"
  ],
  "experience_level": "高级",
  "preferred_task_types": ["programming", "web3", "consulting"],
  "availability": {
    "hours_per_week": 30,
    "timezone": "Asia/Shanghai",
    "preferred_schedule": "flexible"
  },
  "reward_expectations": {
    "min_hourly_rate": 50,
    "preferred_currency": "USDT",
    "payment_preference": "milestone"
  }
}
```

#### 响应示例

```json
{
  "success": true,
  "message": "用户档案已更新，推荐效果将会改善",
  "updated_skills": [
    "solidity",
    "javascript", 
    "python",
    "react",
    "node.js",
    "web3.js",
    "smart-contracts"
  ],
  "updated_interests": [
    "blockchain",
    "defi",
    "nft",
    "dao",
    "fintech",
    "mobile-development"
  ],
  "inferred_task_types": ["programming", "web3", "consulting"],
  "profile_completeness": 0.92,
  "recommendation_improvement_estimate": 0.15,
  "next_steps": [
    "完成技能验证测试",
    "添加作品集链接",
    "设置任务提醒偏好"
  ]
}
```

### 4. 推荐反馈

**POST** `/api/v1/multi-agent/recommendation-feedback`

提供推荐结果的反馈，帮助系统学习和优化。

#### 请求参数

```json
{
  "task_id": 12345,
  "feedback_type": "positive",  // "positive" | "negative" | "neutral"
  "action_taken": "applied",    // "applied" | "saved" | "ignored" | "hidden"
  "feedback_details": {
    "match_accuracy": 4,        // 1-5分
    "relevance": 5,            // 1-5分
    "timing": 4,               // 1-5分
    "reward_satisfaction": 5    // 1-5分
  },
  "comments": "这个推荐很准确，正是我在寻找的项目类型",
  "improvement_suggestions": [
    "可以增加更多技术细节",
    "希望看到项目的技术栈要求"
  ]
}
```

#### 响应示例

```json
{
  "success": true,
  "message": "感谢您的反馈，这将帮助我们改善推荐质量",
  "feedback_id": "feedback_67890",
  "impact_on_future_recommendations": {
    "immediate_adjustments": [
      "增加类似项目的权重",
      "优化技术匹配算法"
    ],
    "learning_points": [
      "用户偏好高技术含量项目",
      "对DeFi领域有强烈兴趣"
    ]
  },
  "reward_points": 10,
  "next_recommendation_eta": "2024-01-15T16:00:00Z"
}
```

### 5. 推荐历史

**GET** `/api/v1/multi-agent/recommendation-history`

获取用户的推荐历史记录和统计信息。

#### 查询参数

- `limit` (可选): 返回记录数，默认20
- `start_date` (可选): 开始日期
- `end_date` (可选): 结束日期
- `status` (可选): 推荐状态过滤 (`shown`, `applied`, `ignored`, `expired`)

#### 响应示例

```json
{
  "history": [
    {
      "recommendation_id": "rec_001",
      "task_id": 12345,
      "task_title": "DeFi协议智能合约开发",
      "recommended_at": "2024-01-15T14:30:00Z",
      "match_score": 0.94,
      "status": "applied",
      "user_action": "submitted_application",
      "action_timestamp": "2024-01-15T15:45:00Z",
      "feedback_given": true,
      "feedback_score": 4.5
    },
    {
      "recommendation_id": "rec_002", 
      "task_id": 12346,
      "task_title": "React Native移动应用开发",
      "recommended_at": "2024-01-15T14:30:00Z",
      "match_score": 0.89,
      "status": "saved",
      "user_action": "bookmarked",
      "action_timestamp": "2024-01-15T14:35:00Z",
      "feedback_given": false
    }
  ],
  "statistics": {
    "total_recommendations": 156,
    "applications_submitted": 23,
    "success_rate": 0.68,
    "average_match_score": 0.84,
    "most_successful_category": "web3",
    "recommendation_accuracy": 0.87,
    "user_satisfaction_score": 4.2
  },
  "trends": {
    "weekly_recommendations": 12,
    "monthly_applications": 8,
    "improvement_over_time": 0.15,
    "preferred_recommendation_times": ["14:00-16:00", "20:00-22:00"]
  }
}
```

### 6. 推荐设置

**GET/PUT** `/api/v1/multi-agent/recommendation-settings`

管理推荐系统的个性化设置。

#### 获取设置 (GET)

```json
{
  "notification_enabled": true,
  "notification_frequency": "daily",
  "notification_time": "09:00",
  "auto_refresh_interval": 3600,
  "max_recommendations_per_day": 20,
  "diversity_preference": 0.7,
  "exploration_vs_exploitation": 0.3,
  "categories_enabled": ["programming", "web3", "design"],
  "blocked_sponsors": ["sponsor_123"],
  "minimum_match_score": 0.6,
  "advanced_filters": {
    "exclude_long_term": false,
    "prefer_remote": true,
    "exclude_low_rated_sponsors": true
  }
}
```

#### 更新设置 (PUT)

```json
{
  "notification_frequency": "weekly",
  "max_recommendations_per_day": 15,
  "diversity_preference": 0.8,
  "minimum_match_score": 0.7,
  "advanced_filters": {
    "exclude_long_term": true,
    "prefer_remote": true
  }
}
```

## 推荐质量指标

### 1. 匹配分数 (Match Score)

- **0.9-1.0**: 完美匹配，强烈推荐
- **0.8-0.9**: 高度匹配，推荐申请
- **0.7-0.8**: 良好匹配，值得考虑
- **0.6-0.7**: 一般匹配，可以查看
- **<0.6**: 匹配度低，不推荐

### 2. 成功概率 (Success Probability)

基于历史数据预测用户获得任务的概率：

- **>0.8**: 很高概率获得任务
- **0.6-0.8**: 较高概率
- **0.4-0.6**: 中等概率
- **<0.4**: 较低概率

### 3. 个性化分数 (Personalization Score)

衡量推荐的个性化程度：

- **>0.9**: 高度个性化
- **0.7-0.9**: 良好个性化
- **0.5-0.7**: 一般个性化
- **<0.5**: 通用推荐

## 最佳实践

### 1. 提高推荐质量

```python
# 定期更新用户档案
def update_profile_regularly():
    # 每月更新技能
    skills = get_current_skills()
    interests = analyze_recent_behavior()
    
    client.update_user_profile(
        skills=skills,
        interests=interests
    )

# 提供高质量反馈
def provide_quality_feedback(task_id, experience):
    feedback = {
        "task_id": task_id,
        "feedback_type": "positive" if experience.satisfied else "negative",
        "action_taken": experience.action,
        "feedback_details": {
            "match_accuracy": experience.match_rating,
            "relevance": experience.relevance_rating,
            "timing": experience.timing_rating,
            "reward_satisfaction": experience.reward_rating
        },
        "comments": experience.detailed_feedback
    }
    
    client.provide_recommendation_feedback(feedback)
```

### 2. 优化查询策略

```python
# 使用自然语言查询
def smart_query_recommendations():
    queries = [
        "找一些Python Web3项目，奖励2000美元以上",
        "有什么适合远程工作的设计任务吗",
        "我想找一些短期的区块链咨询项目"
    ]
    
    for query in queries:
        response = client.ask_recommendations(query)
        if response.matched_tasks_count > 0:
            return response
    
    # 回退到标准推荐
    return client.get_recommendations(limit=10)
```

### 3. 推荐结果处理

```python
def process_recommendations(recommendations):
    # 按匹配分数排序
    sorted_recs = sorted(
        recommendations,
        key=lambda x: x.match_score,
        reverse=True
    )
    
    # 过滤低质量推荐
    quality_recs = [
        rec for rec in sorted_recs
        if rec.match_score >= 0.7 and rec.success_probability >= 0.6
    ]
    
    # 分类处理
    high_priority = [rec for rec in quality_recs if rec.match_score >= 0.9]
    medium_priority = [rec for rec in quality_recs if 0.8 <= rec.match_score < 0.9]
    
    return {
        "high_priority": high_priority,
        "medium_priority": medium_priority,
        "total_quality_count": len(quality_recs)
    }
```

## 集成示例

### React 前端集成

```jsx
import React, { useState, useEffect } from 'react';
import { RecommendationClient } from './api/recommendations';

const RecommendationsPage = () => {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  
  const client = new RecommendationClient(apiToken);

  useEffect(() => {
    loadRecommendations();
  }, []);

  const loadRecommendations = async () => {
    try {
      setLoading(true);
      const response = await client.getRecommendations({ limit: 10 });
      setRecommendations(response.recommendations);
    } catch (error) {
      console.error('加载推荐失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleNaturalQuery = async () => {
    if (!query.trim()) return;
    
    try {
      setLoading(true);
      const response = await client.askRecommendations(query);
      
      if (response.requires_action && response.action_type === 'show_recommendations') {
        // 获取具体推荐
        const recs = await client.getRecommendations({
          category: response.parsed_query.category,
          min_reward: response.parsed_query.min_reward
        });
        setRecommendations(recs.recommendations);
      }
    } catch (error) {
      console.error('查询失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (taskId, feedbackType) => {
    try {
      await client.provideFeedback({
        task_id: taskId,
        feedback_type: feedbackType,
        action_taken: feedbackType === 'positive' ? 'applied' : 'ignored'
      });
      
      // 刷新推荐
      loadRecommendations();
    } catch (error) {
      console.error('反馈提交失败:', error);
    }
  };

  return (
    <div className="recommendations-page">
      <div className="search-section">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="用自然语言描述您想要的任务..."
          className="query-input"
        />
        <button onClick={handleNaturalQuery} className="search-btn">
          智能搜索
        </button>
      </div>

      {loading ? (
        <div className="loading">加载推荐中...</div>
      ) : (
        <div className="recommendations-list">
          {recommendations.map((rec) => (
            <div key={rec.task_id} className="recommendation-card">
              <h3>{rec.title}</h3>
              <p>{rec.description}</p>
              
              <div className="task-meta">
                <span className="reward">{rec.reward} {rec.reward_currency}</span>
                <span className="difficulty">{rec.difficulty_level}</span>
                <span className="match-score">匹配度: {(rec.match_score * 100).toFixed(0)}%</span>
              </div>

              <div className="match-reasons">
                <h4>推荐理由:</h4>
                <ul>
                  {rec.match_reasons.map((reason, index) => (
                    <li key={index}>{reason}</li>
                  ))}
                </ul>
              </div>

              <div className="actions">
                <button 
                  onClick={() => handleFeedback(rec.task_id, 'positive')}
                  className="btn-positive"
                >
                  感兴趣
                </button>
                <button 
                  onClick={() => handleFeedback(rec.task_id, 'negative')}
                  className="btn-negative"
                >
                  不感兴趣
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default RecommendationsPage;
```

### Python 后端集成

```python
from typing import List, Dict, Optional
import asyncio
from datetime import datetime, timedelta

class RecommendationService:
    def __init__(self, client: RecommendationClient):
        self.client = client
        self.cache = {}
        self.cache_ttl = timedelta(hours=1)

    async def get_personalized_recommendations(
        self, 
        user_id: str, 
        limit: int = 10,
        refresh_cache: bool = False
    ) -> Dict:
        """获取个性化推荐"""
        cache_key = f"recommendations_{user_id}_{limit}"
        
        # 检查缓存
        if not refresh_cache and cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                return cached_data

        # 获取新推荐
        recommendations = await self.client.get_recommendations(limit=limit)
        
        # 缓存结果
        self.cache[cache_key] = (recommendations, datetime.now())
        
        return recommendations

    async def process_natural_query(self, user_id: str, query: str) -> Dict:
        """处理自然语言查询"""
        # 先尝试自然语言查询
        response = await self.client.ask_recommendations(query)
        
        if response.get('requires_action') and response.get('matched_tasks_count', 0) > 0:
            # 获取具体推荐
            parsed_query = response.get('parsed_query', {})
            recommendations = await self.client.get_recommendations(
                category=parsed_query.get('category'),
                min_reward=parsed_query.get('min_reward'),
                limit=10
            )
            
            return {
                "query_response": response,
                "recommendations": recommendations,
                "total_matches": response.get('matched_tasks_count', 0)
            }
        
        return {"query_response": response, "recommendations": None}

    async def update_user_profile_smart(self, user_id: str, user_data: Dict):
        """智能更新用户档案"""
        # 分析用户数据
        skills = self._extract_skills(user_data)
        interests = self._infer_interests(user_data)
        
        # 更新档案
        result = await self.client.update_user_profile(
            skills=skills,
            interests=interests
        )
        
        # 如果档案完整度提升显著，刷新推荐缓存
        if result.get('recommendation_improvement_estimate', 0) > 0.1:
            await self._refresh_user_cache(user_id)
        
        return result

    async def batch_feedback_processing(self, feedback_batch: List[Dict]):
        """批量处理反馈"""
        results = []
        
        for feedback in feedback_batch:
            try:
                result = await self.client.provide_feedback(feedback)
                results.append({"success": True, "result": result})
            except Exception as e:
                results.append({"success": False, "error": str(e)})
        
        return results

    def _extract_skills(self, user_data: Dict) -> List[str]:
        """从用户数据提取技能"""
        skills = set()
        
        # 从简历中提取
        if 'resume' in user_data:
            skills.update(self._parse_skills_from_text(user_data['resume']))
        
        # 从项目经验中提取
        if 'projects' in user_data:
            for project in user_data['projects']:
                skills.update(project.get('technologies', []))
        
        return list(skills)

    def _infer_interests(self, user_data: Dict) -> List[str]:
        """推断用户兴趣"""
        interests = set()
        
        # 从搜索历史推断
        if 'search_history' in user_data:
            interests.update(self._analyze_search_patterns(user_data['search_history']))
        
        # 从任务历史推断
        if 'task_history' in user_data:
            interests.update(self._analyze_task_patterns(user_data['task_history']))
        
        return list(interests)

    async def _refresh_user_cache(self, user_id: str):
        """刷新用户相关缓存"""
        cache_keys_to_remove = [
            key for key in self.cache.keys() 
            if key.startswith(f"recommendations_{user_id}")
        ]
        
        for key in cache_keys_to_remove:
            del self.cache[key]

# 使用示例
async def main():
    client = RecommendationClient("http://localhost:8000/api/v1/multi-agent", "token")
    service = RecommendationService(client)
    
    # 获取推荐
    recommendations = await service.get_personalized_recommendations("user123", limit=5)
    print(f"获得 {len(recommendations['recommendations'])} 个推荐")
    
    # 自然语言查询
    query_result = await service.process_natural_query(
        "user123", 
        "我想找一些Python Web3项目，奖励在2000美元以上"
    )
    
    if query_result['recommendations']:
        print(f"查询匹配 {query_result['total_matches']} 个任务")

if __name__ == "__main__":
    asyncio.run(main())
```

## 错误处理

### 常见错误码

- `INSUFFICIENT_USER_DATA` - 用户数据不足，无法生成推荐
- `NO_MATCHING_TASKS` - 没有符合条件的任务
- `RECOMMENDATION_EXPIRED` - 推荐已过期
- `INVALID_FEEDBACK` - 反馈数据无效
- `RATE_LIMIT_EXCEEDED` - 请求频率过高

### 错误处理示例

```python
try:
    recommendations = await client.get_recommendations()
except RecommendationError as e:
    if e.error_code == "INSUFFICIENT_USER_DATA":
        # 引导用户完善档案
        return redirect_to_profile_setup()
    elif e.error_code == "NO_MATCHING_TASKS":
        # 建议调整筛选条件
        return suggest_broader_criteria()
    else:
        # 通用错误处理
        return handle_generic_error(e)
```

## 更新日志

### v1.0.0 (2024-01-15)
- 初始版本发布
- 基于RAG的推荐算法
- 自然语言查询支持
- 用户反馈学习机制
- 个性化推荐设置

### 未来计划
- 实时推荐更新
- 团队推荐功能
- 推荐解释性增强
- 多语言推荐支持
- A/B测试推荐策略