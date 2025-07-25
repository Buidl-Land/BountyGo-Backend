#!/usr/bin/env python3
"""
BountyGo API 全面测试脚本
使用开发测试token进行完整的API功能测试
"""
import requests
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class TestCase:
    name: str
    method: str
    endpoint: str
    headers: Optional[Dict[str, str]] = None
    data: Optional[Dict[str, Any]] = None
    expected_status: int = 200
    expected_keys: Optional[List[str]] = None
    description: str = ""


@dataclass
class TestSuiteResult:
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    results: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = []


class BountyGoAPITester:
    """BountyGo API 测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 10):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.dev_token = None
        self.auth_headers = {}
        self.session = requests.Session()
        
        # 测试结果
        self.suite_result = TestSuiteResult()
        
    def setup(self) -> bool:
        """设置测试环境"""
        logger.info("🔧 设置测试环境...")
        
        # 首先测试基本连接
        try:
            logger.info(f"测试连接到: {self.base_url}")
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            logger.info(f"健康检查响应: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ 无法连接到服务器: {e}")
            logger.info("请确保服务器正在运行: uvicorn app.main:app --reload")
            return False
        
        # 获取开发token
        try:
            response = self.session.get(f"{self.base_url}/api/v1/dev-auth", timeout=self.timeout)
            logger.info(f"开发认证端点响应: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"开发认证响应数据: {data}")
                
                if data.get('status') == '已配置':
                    self.dev_token = data.get('test_token')
                    self.auth_headers = {"Authorization": f"Bearer {self.dev_token}"}
                    logger.info(f"✅ 获取到开发token: {self.dev_token}")
                    return True
                else:
                    logger.error("❌ 开发token未配置")
                    return False
            elif response.status_code == 404:
                logger.error("❌ 开发认证端点不存在，可能不在开发环境")
                return False
            else:
                logger.error(f"❌ 无法获取开发认证信息: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ 设置失败: {e}")
            return False
    
    def execute_test(self, test_case: TestCase) -> Dict[str, Any]:
        """执行单个测试用例"""
        result = {
            "name": test_case.name,
            "status": TestResult.FAIL,
            "expected_status": test_case.expected_status,
            "actual_status": None,
            "response_data": None,
            "error": None,
            "duration": 0
        }
        
        try:
            start_time = time.time()
            
            # 准备请求参数
            url = f"{self.base_url}{test_case.endpoint}"
            headers = test_case.headers or {}
            
            # 发送请求
            if test_case.method.upper() == "GET":
                response = self.session.get(url, headers=headers, timeout=self.timeout)
            elif test_case.method.upper() == "POST":
                response = self.session.post(url, headers=headers, json=test_case.data, timeout=self.timeout)
            elif test_case.method.upper() == "PUT":
                response = self.session.put(url, headers=headers, json=test_case.data, timeout=self.timeout)
            elif test_case.method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=self.timeout)
            else:
                raise ValueError(f"不支持的HTTP方法: {test_case.method}")
            
            result["duration"] = time.time() - start_time
            result["actual_status"] = response.status_code
            
            # 尝试解析JSON响应
            try:
                result["response_data"] = response.json()
            except:
                result["response_data"] = response.text
            
            # 检查状态码
            if response.status_code == test_case.expected_status:
                result["status"] = TestResult.PASS
                
                # 检查响应中是否包含期望的键
                if test_case.expected_keys and isinstance(result["response_data"], dict):
                    missing_keys = []
                    for key in test_case.expected_keys:
                        if key not in result["response_data"]:
                            missing_keys.append(key)
                    
                    if missing_keys:
                        result["status"] = TestResult.FAIL
                        result["error"] = f"响应中缺少期望的键: {missing_keys}"
            else:
                result["error"] = f"状态码不匹配: 期望 {test_case.expected_status}, 实际 {response.status_code}"
                
        except Exception as e:
            result["error"] = str(e)
            result["duration"] = time.time() - start_time if 'start_time' in locals() else 0
        
        return result
    
    def run_test_suite(self, test_cases: List[TestCase], suite_name: str = "API测试") -> TestSuiteResult:
        """运行测试套件"""
        logger.info(f"🚀 开始运行测试套件: {suite_name}")
        logger.info(f"📊 总测试用例数: {len(test_cases)}")
        
        suite_result = TestSuiteResult()
        suite_result.total = len(test_cases)
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"[{i}/{len(test_cases)}] 执行测试: {test_case.name}")
            
            result = self.execute_test(test_case)
            suite_result.results.append(result)
            
            if result["status"] == TestResult.PASS:
                suite_result.passed += 1
                logger.info(f"  ✅ 通过 ({result['duration']:.2f}s)")
            elif result["status"] == TestResult.FAIL:
                suite_result.failed += 1
                logger.error(f"  ❌ 失败: {result['error']}")
            else:
                suite_result.skipped += 1
                logger.warning(f"  ⏭️ 跳过")
            
            # 显示响应摘要
            if result["response_data"]:
                if isinstance(result["response_data"], dict):
                    keys = list(result["response_data"].keys())[:5]
                    logger.info(f"    响应键: {keys}")
                elif isinstance(result["response_data"], str) and len(result["response_data"]) > 100:
                    logger.info(f"    响应: {result['response_data'][:100]}...")
                else:
                    logger.info(f"    响应: {result['response_data']}")
        
        return suite_result
    
    def create_test_cases(self) -> List[TestCase]:
        """创建测试用例"""
        test_cases = []
        
        # 1. 系统信息端点
        test_cases.extend([
            TestCase(
                name="健康检查",
                method="GET",
                endpoint="/health",
                expected_status=200,
                description="检查API服务健康状态"
            ),
            TestCase(
                name="API信息",
                method="GET",
                endpoint="/api/v1/",
                expected_status=200,
                expected_keys=["message", "version", "status"],
                description="获取API基本信息"
            ),
            TestCase(
                name="开发认证信息",
                method="GET",
                endpoint="/api/v1/dev-auth",
                expected_status=200,
                expected_keys=["message", "status", "test_token"],
                description="获取开发环境认证信息"
            ),
        ])
        
        # 2. 认证错误测试
        test_cases.extend([
            TestCase(
                name="无认证头访问保护端点",
                method="GET",
                endpoint="/api/v1/users/me",
                expected_status=401,
                description="测试无认证头时的错误提示"
            ),
            TestCase(
                name="空token访问保护端点",
                method="GET",
                endpoint="/api/v1/users/me",
                headers={"Authorization": "Bearer "},
                expected_status=401,
                description="测试空token时的错误提示"
            ),
            TestCase(
                name="null token访问保护端点",
                method="GET",
                endpoint="/api/v1/users/me",
                headers={"Authorization": "Bearer null"},
                expected_status=401,
                description="测试null token时的错误提示"
            ),
            TestCase(
                name="无效token访问保护端点",
                method="GET",
                endpoint="/api/v1/users/me",
                headers={"Authorization": "Bearer invalid-token-123"},
                expected_status=401,
                description="测试无效token时的错误提示"
            ),
        ])
        
        # 3. 开发token认证测试
        test_cases.extend([
            TestCase(
                name="使用开发token获取当前用户",
                method="GET",
                endpoint="/api/v1/users/me",
                headers=self.auth_headers,
                expected_status=200,
                expected_keys=["id", "email", "nickname", "is_active"],
                description="使用开发token访问用户信息"
            ),
            TestCase(
                name="使用开发token获取用户钱包",
                method="GET",
                endpoint="/api/v1/users/me/wallets",
                headers=self.auth_headers,
                expected_status=200,
                description="使用开发token访问用户钱包信息"
            ),
        ])
        
        # 4. 公开端点测试
        test_cases.extend([
            TestCase(
                name="获取任务列表",
                method="GET",
                endpoint="/api/v1/tasks",
                expected_status=200,
                description="获取公开任务列表"
            ),
            TestCase(
                name="获取任务列表(分页)",
                method="GET",
                endpoint="/api/v1/tasks?page=1&size=5",
                expected_status=200,
                description="获取分页任务列表"
            ),
            TestCase(
                name="搜索任务",
                method="GET",
                endpoint="/api/v1/tasks?search=test",
                expected_status=200,
                description="搜索任务功能"
            ),
            TestCase(
                name="获取标签列表",
                method="GET",
                endpoint="/api/v1/tags",
                expected_status=200,
                description="获取标签列表"
            ),
            TestCase(
                name="获取标签分类",
                method="GET",
                endpoint="/api/v1/tags/categories",
                expected_status=200,
                description="获取标签分类列表"
            ),
            TestCase(
                name="搜索标签",
                method="GET",
                endpoint="/api/v1/tags/search?q=python",
                expected_status=200,
                description="搜索标签功能"
            ),
        ])
        
        # 5. 分析端点测试
        test_cases.extend([
            TestCase(
                name="获取系统统计",
                method="GET",
                endpoint="/api/v1/analytics/system",
                expected_status=200,
                description="获取系统统计信息"
            ),
            TestCase(
                name="获取热门标签",
                method="GET",
                endpoint="/api/v1/analytics/popular-tags",
                expected_status=200,
                description="获取热门标签统计"
            ),
            TestCase(
                name="获取最近活动",
                method="GET",
                endpoint="/api/v1/analytics/recent-activity",
                expected_status=200,
                description="获取最近活动信息"
            ),
            TestCase(
                name="获取个人统计(需认证)",
                method="GET",
                endpoint="/api/v1/analytics/me",
                headers=self.auth_headers,
                expected_status=200,
                description="获取个人统计数据"
            ),
            TestCase(
                name="获取发布者仪表板(需认证)",
                method="GET",
                endpoint="/api/v1/analytics/sponsor-dashboard",
                headers=self.auth_headers,
                expected_status=200,
                description="获取发布者仪表板数据"
            ),
        ])
        
        # 6. 用户相关端点测试
        test_cases.extend([
            TestCase(
                name="更新用户配置文件",
                method="PUT",
                endpoint="/api/v1/users/me",
                headers=self.auth_headers,
                data={"nickname": "测试用户更新"},
                expected_status=200,
                description="更新用户配置文件"
            ),
        ])
        
        # 7. 标签配置测试
        test_cases.extend([
            TestCase(
                name="获取个人标签配置",
                method="GET",
                endpoint="/api/v1/tags/me/profile",
                headers=self.auth_headers,
                expected_status=200,
                description="获取个人标签配置"
            ),
        ])
        
        # 8. 错误端点测试
        test_cases.extend([
            TestCase(
                name="访问不存在的端点",
                method="GET",
                endpoint="/api/v1/nonexistent",
                expected_status=404,
                description="测试404错误处理"
            ),
            TestCase(
                name="访问不存在的任务",
                method="GET",
                endpoint="/api/v1/tasks/99999",
                expected_status=404,
                description="测试资源不存在错误"
            ),
        ])
        
        return test_cases
    
    def print_summary(self, suite_result: TestSuiteResult):
        """打印测试结果摘要"""
        print("\n" + "="*60)
        print("🎯 测试结果摘要")
        print("="*60)
        print(f"总测试数: {suite_result.total}")
        print(f"✅ 通过: {suite_result.passed}")
        print(f"❌ 失败: {suite_result.failed}")
        print(f"⏭️ 跳过: {suite_result.skipped}")
        
        success_rate = (suite_result.passed / suite_result.total * 100) if suite_result.total > 0 else 0
        print(f"📊 成功率: {success_rate:.1f}%")
        
        if suite_result.failed > 0:
            print(f"\n❌ 失败的测试:")
            for result in suite_result.results:
                if result["status"] == TestResult.FAIL:
                    print(f"  - {result['name']}: {result['error']}")
        
        print("\n" + "="*60)
        
        if suite_result.failed == 0:
            print("🎉 所有测试通过！")
            return True
        else:
            print(f"⚠️ 有 {suite_result.failed} 个测试失败")
            return False
    
    def save_results(self, suite_result: TestSuiteResult, filename: str = "test_results.json"):
        """保存测试结果到文件"""
        results_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "base_url": self.base_url,
            "dev_token": self.dev_token,
            "summary": {
                "total": suite_result.total,
                "passed": suite_result.passed,
                "failed": suite_result.failed,
                "skipped": suite_result.skipped,
                "success_rate": (suite_result.passed / suite_result.total * 100) if suite_result.total > 0 else 0
            },
            "results": suite_result.results
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)
            logger.info(f"📄 测试结果已保存到: {filename}")
        except Exception as e:
            logger.error(f"❌ 保存测试结果失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="BountyGo API 全面测试")
    parser.add_argument("--url", default="http://localhost:8000", help="API基础URL")
    parser.add_argument("--timeout", type=int, default=10, help="请求超时时间(秒)")
    parser.add_argument("--save", help="保存测试结果到文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 创建测试器
    tester = BountyGoAPITester(args.url, args.timeout)
    
    # 设置测试环境
    if not tester.setup():
        logger.error("❌ 测试环境设置失败")
        sys.exit(1)
    
    # 创建测试用例
    test_cases = tester.create_test_cases()
    
    # 运行测试
    suite_result = tester.run_test_suite(test_cases, "BountyGo API 全面测试")
    
    # 打印结果摘要
    success = tester.print_summary(suite_result)
    
    # 保存结果
    if args.save:
        tester.save_results(suite_result, args.save)
    
    # 退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()