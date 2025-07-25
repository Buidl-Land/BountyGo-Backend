# BountyGo Backend Scripts

这个目录包含了BountyGo后端的实用脚本。

## 脚本说明

### 开发环境设置
- **`setup_dev_env.py`** - 自动配置开发环境，生成测试token
- **`test_db_connection.py`** - 诊断和测试数据库连接

### API测试
- **`comprehensive_api_test.py`** - 完整的API测试框架，支持详细报告
- **`simple_api_test.py`** - 简化的API测试脚本，使用curl命令

### 数据库管理
- **`init_database.py`** - 数据库初始化脚本
- **`init-db.sql`** - SQL初始化脚本

## 使用方法

### 快速开始
```bash
# 1. 设置开发环境
python scripts/setup_dev_env.py

# 2. 测试数据库连接
python scripts/test_db_connection.py

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