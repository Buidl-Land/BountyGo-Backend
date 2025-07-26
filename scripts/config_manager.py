#!/usr/bin/env python3
"""
Configuration Management Script for BountyGo Backend
配置管理脚本 - 用于生产环境配置管理和验证
"""
import os
import sys
import json
import yaml
import argparse
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import subprocess
import secrets
import hashlib

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import Settings


@dataclass
class ConfigValidationResult:
    """配置验证结果"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    recommendations: List[str]


@dataclass
class EnvironmentConfig:
    """环境配置"""
    name: str
    description: str
    required_vars: List[str]
    optional_vars: List[str]
    validation_rules: Dict[str, Any]


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.logger = self._setup_logging()
        
        # 环境配置定义
        self.environments = {
            "development": EnvironmentConfig(
                name="development",
                description="开发环境",
                required_vars=[
                    "SECRET_KEY", "DATABASE_URL", "GOOGLE_CLIENT_ID", 
                    "GOOGLE_CLIENT_SECRET", "PPIO_API_KEY"
                ],
                optional_vars=[
                    "REDIS_URL", "DEBUG", "DEV_TEST_TOKEN"
                ],
                validation_rules={
                    "DEBUG": {"type": "bool", "default": True},
                    "ENVIRONMENT": {"type": "str", "allowed": ["development"]},
                    "PPIO_TIMEOUT": {"type": "int", "min": 30, "max": 300}
                }
            ),
            "production": EnvironmentConfig(
                name="production",
                description="生产环境",
                required_vars=[
                    "SECRET_KEY", "DATABASE_URL", "GOOGLE_CLIENT_ID", 
                    "GOOGLE_CLIENT_SECRET", "PPIO_API_KEY", "POSTGRES_PASSWORD"
                ],
                optional_vars=[
                    "REDIS_URL", "REDIS_PASSWORD", "ALLOWED_HOSTS"
                ],
                validation_rules={
                    "DEBUG": {"type": "bool", "default": False, "required_value": False},
                    "ENVIRONMENT": {"type": "str", "allowed": ["production"], "required_value": "production"},
                    "SECRET_KEY": {"type": "str", "min_length": 32},
                    "PPIO_TIMEOUT": {"type": "int", "min": 60, "max": 300},
                    "VERIFY_SSL": {"type": "bool", "default": True, "required_value": True}
                }
            ),
            "testing": EnvironmentConfig(
                name="testing",
                description="测试环境",
                required_vars=[
                    "SECRET_KEY", "DATABASE_URL", "PPIO_API_KEY"
                ],
                optional_vars=[
                    "REDIS_URL", "DEBUG"
                ],
                validation_rules={
                    "DEBUG": {"type": "bool", "default": True},
                    "ENVIRONMENT": {"type": "str", "allowed": ["testing"]},
                    "DATABASE_URL": {"type": "str", "pattern": r".*test.*"}
                }
            )
        }
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def validate_environment(self, env_name: str, env_file: Optional[str] = None) -> ConfigValidationResult:
        """验证环境配置"""
        if env_name not in self.environments:
            return ConfigValidationResult(
                valid=False,
                errors=[f"Unknown environment: {env_name}"],
                warnings=[],
                recommendations=[]
            )
        
        env_config = self.environments[env_name]
        result = ConfigValidationResult(valid=True, errors=[], warnings=[], recommendations=[])
        
        # 加载环境变量
        if env_file:
            self._load_env_file(env_file)
        
        # 验证必需变量
        for var in env_config.required_vars:
            if not os.getenv(var):
                result.errors.append(f"Required environment variable missing: {var}")
                result.valid = False
        
        # 验证配置规则
        for var, rules in env_config.validation_rules.items():
            value = os.getenv(var)
            
            if value is None:
                if "default" in rules:
                    result.warnings.append(f"{var} not set, using default: {rules['default']}")
                continue
            
            # 类型验证
            if "type" in rules:
                if not self._validate_type(var, value, rules["type"]):
                    result.errors.append(f"{var} has invalid type, expected: {rules['type']}")
                    result.valid = False
            
            # 值验证
            if "allowed" in rules and value not in rules["allowed"]:
                result.errors.append(f"{var} has invalid value, allowed: {rules['allowed']}")
                result.valid = False
            
            if "required_value" in rules and value != str(rules["required_value"]):
                result.errors.append(f"{var} must be: {rules['required_value']}")
                result.valid = False
            
            # 长度验证
            if "min_length" in rules and len(value) < rules["min_length"]:
                result.errors.append(f"{var} is too short, minimum length: {rules['min_length']}")
                result.valid = False
            
            # 数值范围验证
            if rules.get("type") == "int":
                try:
                    int_value = int(value)
                    if "min" in rules and int_value < rules["min"]:
                        result.errors.append(f"{var} is too small, minimum: {rules['min']}")
                        result.valid = False
                    if "max" in rules and int_value > rules["max"]:
                        result.errors.append(f"{var} is too large, maximum: {rules['max']}")
                        result.valid = False
                except ValueError:
                    result.errors.append(f"{var} is not a valid integer")
                    result.valid = False
        
        # 应用程序特定验证
        try:
            settings = Settings()
            
            # PPIO配置验证
            ppio_validation = settings.validate_ppio_config()
            if not ppio_validation["valid"]:
                result.errors.extend(ppio_validation["errors"])
                result.valid = False
            result.warnings.extend(ppio_validation["warnings"])
            
            # URL Agent配置验证
            url_validation = settings.validate_url_agent_config()
            if not url_validation["valid"]:
                result.errors.extend(url_validation["errors"])
                result.valid = False
            result.warnings.extend(url_validation["warnings"])
            
            # 生产环境特定验证
            if env_name == "production":
                prod_validation = settings.validate_production_config()
                if not prod_validation["valid"]:
                    result.errors.extend(prod_validation["errors"])
                    result.valid = False
                result.warnings.extend(prod_validation["warnings"])
            
        except Exception as e:
            result.errors.append(f"Settings validation failed: {str(e)}")
            result.valid = False
        
        # 生成建议
        self._generate_recommendations(env_name, result)
        
        return result
    
    def _validate_type(self, var: str, value: str, expected_type: str) -> bool:
        """验证变量类型"""
        try:
            if expected_type == "bool":
                return value.lower() in ["true", "false", "1", "0", "yes", "no"]
            elif expected_type == "int":
                int(value)
                return True
            elif expected_type == "float":
                float(value)
                return True
            elif expected_type == "str":
                return True
            else:
                return False
        except (ValueError, AttributeError):
            return False
    
    def _load_env_file(self, env_file: str) -> None:
        """加载环境文件"""
        env_path = self.project_root / env_file
        if not env_path.exists():
            self.logger.warning(f"Environment file not found: {env_file}")
            return
        
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"\'')
    
    def _generate_recommendations(self, env_name: str, result: ConfigValidationResult) -> None:
        """生成配置建议"""
        if env_name == "production":
            result.recommendations.extend([
                "Use strong, randomly generated SECRET_KEY",
                "Enable SSL/TLS for all external connections",
                "Set up proper backup strategy for database",
                "Configure monitoring and alerting",
                "Use environment-specific API keys",
                "Enable rate limiting in production",
                "Set up log rotation and retention policies"
            ])
        elif env_name == "development":
            result.recommendations.extend([
                "Use development-specific API keys",
                "Enable debug mode for easier troubleshooting",
                "Consider using local database for development",
                "Set up development-specific logging"
            ])
    
    def generate_env_template(self, env_name: str, output_file: Optional[str] = None) -> str:
        """生成环境配置模板"""
        if env_name not in self.environments:
            raise ValueError(f"Unknown environment: {env_name}")
        
        env_config = self.environments[env_name]
        template_lines = [
            f"# {env_config.description}配置文件",
            f"# Generated on {datetime.now().isoformat()}",
            "",
            "# Environment Configuration",
            f"ENVIRONMENT={env_name}",
            ""
        ]
        
        # 必需变量
        template_lines.extend([
            "# Required Variables",
            "# 必需变量"
        ])
        
        for var in env_config.required_vars:
            if var == "SECRET_KEY":
                template_lines.append(f"{var}={self._generate_secret_key()}")
            elif var == "DATABASE_URL":
                if env_name == "production":
                    template_lines.append(f"{var}=postgresql+asyncpg://user:password@localhost:5432/bountygo")
                else:
                    template_lines.append(f"{var}=postgresql+asyncpg://bountygo:bountygo123@localhost:5432/bountygo")
            elif var == "POSTGRES_PASSWORD":
                template_lines.append(f"{var}={self._generate_password()}")
            else:
                template_lines.append(f"{var}=your_{var.lower()}_here")
        
        template_lines.append("")
        
        # 可选变量
        template_lines.extend([
            "# Optional Variables",
            "# 可选变量"
        ])
        
        for var in env_config.optional_vars:
            rules = env_config.validation_rules.get(var, {})
            default_value = rules.get("default", "")
            
            if var == "REDIS_URL":
                default_value = "redis://localhost:6379/0"
            elif var == "REDIS_PASSWORD":
                default_value = self._generate_password()
            elif var == "ALLOWED_HOSTS":
                default_value = "*" if env_name == "development" else "yourdomain.com"
            
            template_lines.append(f"# {var}={default_value}")
        
        template_lines.extend([
            "",
            "# Application Configuration",
            "# 应用程序配置"
        ])
        
        # 应用程序特定配置
        app_config = self._get_app_config_template(env_name)
        template_lines.extend(app_config)
        
        template_content = "\n".join(template_lines)
        
        if output_file:
            output_path = self.project_root / output_file
            with open(output_path, 'w') as f:
                f.write(template_content)
            self.logger.info(f"Environment template written to: {output_file}")
        
        return template_content
    
    def _get_app_config_template(self, env_name: str) -> List[str]:
        """获取应用程序配置模板"""
        if env_name == "production":
            return [
                "DEBUG=false",
                "",
                "# PPIO Configuration",
                "PPIO_API_KEY=sk_your_ppio_api_key_here",
                "PPIO_BASE_URL=https://api.ppinfra.com/v3/openai",
                "PPIO_MODEL_NAME=qwen/qwen3-coder-480b-a35b-instruct",
                "PPIO_MAX_TOKENS=4000",
                "PPIO_TEMPERATURE=0.1",
                "PPIO_TIMEOUT=120",
                "PPIO_MAX_RETRIES=3",
                "",
                "# Content Extraction Configuration",
                "CONTENT_EXTRACTION_TIMEOUT=60",
                "MAX_CONTENT_LENGTH=100000",
                "USE_PROXY=false",
                "ENABLE_CONTENT_CACHE=true",
                "CONTENT_CACHE_TTL=7200",
                "USER_AGENT=BountyGo-URLAgent/1.0",
                "MAX_REDIRECTS=5",
                "VERIFY_SSL=true",
                "",
                "# Performance Configuration",
                "DATABASE_POOL_SIZE=20",
                "DATABASE_MAX_OVERFLOW=40",
                "REDIS_CACHE_TTL=3600",
                "RATE_LIMIT_PER_MINUTE=100",
                "",
                "# Security Configuration",
                "ACCESS_TOKEN_EXPIRE_MINUTES=15",
                "REFRESH_TOKEN_EXPIRE_DAYS=30",
                "JWT_ALGORITHM=HS256"
            ]
        else:
            return [
                "DEBUG=true",
                "",
                "# PPIO Configuration",
                "PPIO_API_KEY=sk_your_ppio_api_key_here",
                "PPIO_BASE_URL=https://api.ppinfra.com/v3/openai",
                "PPIO_MODEL_NAME=qwen/qwen3-coder-480b-a35b-instruct",
                "PPIO_MAX_TOKENS=4000",
                "PPIO_TEMPERATURE=0.1",
                "PPIO_TIMEOUT=60",
                "PPIO_MAX_RETRIES=3",
                "",
                "# Content Extraction Configuration",
                "CONTENT_EXTRACTION_TIMEOUT=30",
                "MAX_CONTENT_LENGTH=50000",
                "USE_PROXY=false",
                "ENABLE_CONTENT_CACHE=true",
                "CONTENT_CACHE_TTL=3600",
                "USER_AGENT=BountyGo-URLAgent/1.0",
                "MAX_REDIRECTS=5",
                "VERIFY_SSL=true",
                "",
                "# Development Configuration",
                "DEV_TEST_TOKEN=dev_test_token_123",
                "DEV_TEST_USER_EMAIL=dev@bountygo.com",
                "DEV_TEST_USER_NICKNAME=开发测试用户"
            ]
    
    def _generate_secret_key(self) -> str:
        """生成安全密钥"""
        return secrets.token_urlsafe(32)
    
    def _generate_password(self) -> str:
        """生成密码"""
        return secrets.token_urlsafe(16)
    
    def backup_config(self, env_name: str) -> str:
        """备份配置"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.project_root / "backups" / "config"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_file = backup_dir / f"{env_name}_config_{timestamp}.json"
        
        config_data = {
            "environment": env_name,
            "timestamp": timestamp,
            "variables": {}
        }
        
        env_config = self.environments[env_name]
        all_vars = env_config.required_vars + env_config.optional_vars
        
        for var in all_vars:
            value = os.getenv(var)
            if value:
                # 不保存敏感信息的实际值
                if any(sensitive in var.lower() for sensitive in ["key", "password", "secret", "token"]):
                    config_data["variables"][var] = f"<{var.lower()}_hash:{hashlib.md5(value.encode()).hexdigest()[:8]}>"
                else:
                    config_data["variables"][var] = value
        
        with open(backup_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        self.logger.info(f"Configuration backed up to: {backup_file}")
        return str(backup_file)
    
    def compare_configs(self, env1: str, env2: str) -> Dict[str, Any]:
        """比较两个环境的配置"""
        if env1 not in self.environments or env2 not in self.environments:
            raise ValueError("Invalid environment names")
        
        config1 = self.environments[env1]
        config2 = self.environments[env2]
        
        comparison = {
            "environments": [env1, env2],
            "required_vars": {
                "common": list(set(config1.required_vars) & set(config2.required_vars)),
                f"only_in_{env1}": list(set(config1.required_vars) - set(config2.required_vars)),
                f"only_in_{env2}": list(set(config2.required_vars) - set(config1.required_vars))
            },
            "optional_vars": {
                "common": list(set(config1.optional_vars) & set(config2.optional_vars)),
                f"only_in_{env1}": list(set(config1.optional_vars) - set(config2.optional_vars)),
                f"only_in_{env2}": list(set(config2.optional_vars) - set(config1.optional_vars))
            },
            "validation_rules": {
                "common": {},
                f"only_in_{env1}": {},
                f"only_in_{env2}": {}
            }
        }
        
        # 比较验证规则
        all_vars = set(config1.validation_rules.keys()) | set(config2.validation_rules.keys())
        
        for var in all_vars:
            rules1 = config1.validation_rules.get(var, {})
            rules2 = config2.validation_rules.get(var, {})
            
            if rules1 and rules2:
                comparison["validation_rules"]["common"][var] = {
                    env1: rules1,
                    env2: rules2
                }
            elif rules1:
                comparison["validation_rules"][f"only_in_{env1}"][var] = rules1
            elif rules2:
                comparison["validation_rules"][f"only_in_{env2}"][var] = rules2
        
        return comparison
    
    def get_config_summary(self, env_name: str) -> Dict[str, Any]:
        """获取配置摘要"""
        if env_name not in self.environments:
            raise ValueError(f"Unknown environment: {env_name}")
        
        env_config = self.environments[env_name]
        
        # 加载当前环境变量
        current_vars = {}
        all_vars = env_config.required_vars + env_config.optional_vars
        
        for var in all_vars:
            value = os.getenv(var)
            if value:
                # 隐藏敏感信息
                if any(sensitive in var.lower() for sensitive in ["key", "password", "secret", "token"]):
                    current_vars[var] = "<hidden>"
                else:
                    current_vars[var] = value
            else:
                current_vars[var] = "<not_set>"
        
        return {
            "environment": env_name,
            "description": env_config.description,
            "required_vars_count": len(env_config.required_vars),
            "optional_vars_count": len(env_config.optional_vars),
            "validation_rules_count": len(env_config.validation_rules),
            "current_variables": current_vars,
            "missing_required": [
                var for var in env_config.required_vars 
                if not os.getenv(var)
            ]
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="BountyGo Configuration Manager")
    parser.add_argument("--env", choices=["development", "production", "testing"], 
                       default="development", help="Environment name")
    parser.add_argument("--action", choices=["validate", "template", "backup", "compare", "summary"], 
                       default="validate", help="Action to perform")
    parser.add_argument("--env-file", help="Environment file to load")
    parser.add_argument("--output", help="Output file for template generation")
    parser.add_argument("--compare-with", help="Environment to compare with")
    
    args = parser.parse_args()
    
    config_manager = ConfigManager(project_root)
    
    try:
        if args.action == "validate":
            result = config_manager.validate_environment(args.env, args.env_file)
            
            print(f"\n=== Configuration Validation for {args.env} ===")
            print(f"Valid: {'✅ Yes' if result.valid else '❌ No'}")
            
            if result.errors:
                print(f"\n❌ Errors ({len(result.errors)}):")
                for error in result.errors:
                    print(f"  - {error}")
            
            if result.warnings:
                print(f"\n⚠️  Warnings ({len(result.warnings)}):")
                for warning in result.warnings:
                    print(f"  - {warning}")
            
            if result.recommendations:
                print(f"\n💡 Recommendations ({len(result.recommendations)}):")
                for rec in result.recommendations:
                    print(f"  - {rec}")
            
            sys.exit(0 if result.valid else 1)
        
        elif args.action == "template":
            template = config_manager.generate_env_template(args.env, args.output)
            if not args.output:
                print(template)
        
        elif args.action == "backup":
            backup_file = config_manager.backup_config(args.env)
            print(f"Configuration backed up to: {backup_file}")
        
        elif args.action == "compare":
            if not args.compare_with:
                print("Error: --compare-with is required for compare action")
                sys.exit(1)
            
            comparison = config_manager.compare_configs(args.env, args.compare_with)
            print(json.dumps(comparison, indent=2))
        
        elif args.action == "summary":
            summary = config_manager.get_config_summary(args.env)
            print(json.dumps(summary, indent=2))
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()