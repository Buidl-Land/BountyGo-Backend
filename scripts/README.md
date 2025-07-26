# BountyGo Backend Scripts

这个目录包含了BountyGo后端的实用脚本。

## 🚀 快速开始

### 完整数据库设置（推荐）
```bash
cd backend
python scripts/setup_database.py
```
这个脚本会自动执行：
1. 运行数据库迁移
2. 初始化数据库表
3. 创建测试用户
4. 插入种子数据

## 📋 脚本说明

### 数据库管理
- **`setup_database.py`** - 🌟 **完整数据库设置**（迁移+初始化+种子数据）
- **`init_database.py`** - 数据库初始化脚本
- **`simple_seed.py`** - 插入基础种子数据（3个示例任务）
- **`seed_tasks.py`** - 插入完整测试数据
- **`init-db.sql`** - SQL初始化脚本

### 开发环境设置
- **`setup_dev_env.py`** - 自动配置开发环境，生成测试token
- **`validate_config.py`** - 验证配置设置
- **`validate_dependencies.py`** - 检查依赖安装

### 验证脚本
- **`verify_deadline_migration.py`** - 验证deadline字段迁移是否成功

## 🔧 手动设置（分步执行）

如果你想分步执行：

```bash
cd backend

# 1. 运行数据库迁移
alembic upgrade head

# 2. 初始化数据库表
python scripts/init_database.py

# 3. 插入基础种子数据
python scripts/simple_seed.py

# 3. 运行API测试
python scripts/simple_api_test.py
```

### 详细测试
```bash
# 运行完整的API测试套件
python scripts/comprehensive_api_test.py --verbose

# 保存测试结果
python scripts/comprehensive_api_test.py --save test_results.json
```

## 开发测试token

所有测试脚本都支持开发测试token功能，无需Google OAuth即可测试API：

1. 在`.env`文件中设置`DEV_TEST_TOKEN`
2. 使用`setup_dev_env.py`自动生成安全token
3. 测试脚本会自动使用该token进行认证测试

详细说明请参考：`../docs/DEV_AUTH_GUIDE.md`

## 插入测试任务数据

为了方便前端排版测试，可以使用以下脚本插入3个测试任务：

```bash
# 推荐使用（更稳定）
python scripts/simple_seed.py

# 或者使用ORM版本
python scripts/seed_tasks.py
```

### 测试数据包含：

1. **ETH Global 2024 黑客松大赛** (黑客松分类)
   - 主办方: 以太坊基金会 (已验证)
   - 浏览量: 156, 参与: 23人

2. **Polygon zkEVM 生态征文活动** (征文分类)
   - 主办方: Polygon Labs (已验证)
   - 浏览量: 89, 参与: 12人

3. **Web3 Meme 创作大赛** (Meme创作分类)
   - 主办方: Web3社区 (未验证)
   - 浏览量: 234, 参与: 67人

这些数据涵盖了不同的任务分类、主办方验证状态和互动数据，非常适合前端排版和功能测试。

### 清理测试数据

如需清理，可以直接在数据库中运行：

```sql
DELETE FROM tasks WHERE title LIKE '%ETH Global%' OR title LIKE '%Polygon zkEVM%' OR title LIKE '%Meme 创作%';
DELETE FROM organizers WHERE name IN ('以太坊基金会', 'Polygon Labs', 'Web3社区');
DELETE FROM users WHERE email = 'test@example.com';
```