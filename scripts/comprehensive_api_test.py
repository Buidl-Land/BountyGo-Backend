#!/usr/bin/env python3
"""
全面的API端点测试脚本
"""
import sys
import os
from pathlib import Path
import subprocess
import time
import requests
import json
import threading
from datetime import datetime

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APITester:
    def __init__(self, base_url="http://localhost:8003"):
        self.base_url = base_url
        self.server_process = None
        self.test_results = []
    
    def log_test_result(self, test_name, success, details=None, response_data=None):
        """记录测试结果"""
        result = {
            "test": test_name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details,
            "response_data": response_data
        }
        self.test_results.append(result)
        
        if success:
            logger.info(f"✅ {test_name}")
            if details:
                logger.info(f"   {details}")
        else:
            logger.error(f"❌ {test_name}")
            if details:
                logger.error(f"   {details}")
    
    def start_server(self):
        """启动FastAPI服务器"""
        try:
            logger.info("🚀 启动FastAPI服务器...")
            
            # 启动服务器
            self.server_process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "app.main:app", 
                "--host", "0.0.0.0", 
                "--port", "8003",
                "--log-level", "warning"  # 减少日志输出
            ], cwd=Path(__file__).parent.parent, 
               stdout=subprocess.PIPE, 
               stderr=subprocess.PIPE)
            
            # 等待服务器启动
            logger.info("⏳ 等待服务器启动...")
            time.sleep(8)  # 增加等待时间
            
            # 测试服务器是否启动成功
            try:
                response = requests.get(f"{self.base_url}/", timeout=5)
                if response.status_code in [200, 404]:  # 404也表示服务器在运行
                    logger.info("✅ 服务器启动成功")
                    return True
            except:
                pass
            
            logger.warning("⚠️ 服务器可能未完全启动，继续测试...")
            return True
            
        except Exception as e:
            logger.error(f"❌ 启动服务器失败: {e}")
            return False
    
    def stop_server(self):
        """停止服务器"""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                logger.info("🛑 服务器已停止")
            except:
                self.server_process.kill()
                logger.info("🛑 服务器已强制停止")
    
    def test_basic_endpoints(self):
        """测试基本端点"""
        logger.info("🔍 测试基本端点...")
        
        # 测试根端点
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 404:
                self.log_test_result("根端点", True, "返回404是正常的（未定义根路由）")
            else:
                self.log_test_result("根端点", response.status_code == 200, 
                                   f"状态码: {response.status_code}")
        except Exception as e:
            self.log_test_result("根端点", False, f"连接失败: {e}")
        
        # 测试健康检查
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            success = response.status_code == 200
            data = response.json() if success else None
            self.log_test_result("健康检查端点", success, 
                               f"状态码: {response.status_code}", data)
        except Exception as e:
            self.log_test_result("健康检查端点", False, f"请求失败: {e}")
    
    def test_documentation_endpoints(self):
        """测试文档端点"""
        logger.info("📚 测试文档端点...")
        
        # 测试Swagger UI
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=10)
            success = response.status_code == 200
            self.log_test_result("Swagger UI", success, 
                               f"状态码: {response.status_code}")
        except Exception as e:
            self.log_test_result("Swagger UI", False, f"请求失败: {e}")
        
        # 测试ReDoc
        try:
            response = requests.get(f"{self.base_url}/redoc", timeout=10)
            success = response.status_code == 200
            self.log_test_result("ReDoc文档", success, 
                               f"状态码: {response.status_code}")
        except Exception as e:
            self.log_test_result("ReDoc文档", False, f"请求失败: {e}")
        
        # 测试OpenAPI规范
        try:
            response = requests.get(f"{self.base_url}/openapi.json", timeout=10)
            success = response.status_code == 200
            data = response.json() if success else None
            self.log_test_result("OpenAPI规范", success, 
                               f"状态码: {response.status_code}", 
                               {"title": data.get("info", {}).get("title")} if data else None)
        except Exception as e:
            self.log_test_result("OpenAPI规范", False, f"请求失败: {e}")
    
    def test_api_v1_endpoints(self):
        """测试API v1端点"""
        logger.info("🔌 测试API v1端点...")
        
        # 测试认证端点
        auth_endpoints = [
            "/api/v1/auth/refresh",
            "/api/v1/auth/google", 
            "/api/v1/auth/wallet"
        ]
        
        for endpoint in auth_endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                # 认证端点通常返回401或405是正常的
                success = response.status_code in [401, 405, 422]
                self.log_test_result(f"认证端点 {endpoint}", success, 
                                   f"状态码: {response.status_code}")
            except Exception as e:
                self.log_test_result(f"认证端点 {endpoint}", False, f"请求失败: {e}")
        
        # 测试其他可能的端点
        other_endpoints = [
            "/api/v1/users/me",
            "/api/v1/tasks",
            "/api/v1/tags"
        ]
        
        for endpoint in other_endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                # 这些端点可能返回401（需要认证）或404（未实现）
                success = response.status_code in [401, 404, 422]
                self.log_test_result(f"API端点 {endpoint}", success, 
                                   f"状态码: {response.status_code}")
            except Exception as e:
                self.log_test_result(f"API端点 {endpoint}", False, f"请求失败: {e}")
    
    def test_error_handling(self):
        """测试错误处理"""
        logger.info("⚠️ 测试错误处理...")
        
        # 测试不存在的端点
        try:
            response = requests.get(f"{self.base_url}/nonexistent", timeout=10)
            success = response.status_code == 404
            self.log_test_result("404错误处理", success, 
                               f"状态码: {response.status_code}")
        except Exception as e:
            self.log_test_result("404错误处理", False, f"请求失败: {e}")
        
        # 测试无效的API端点
        try:
            response = requests.get(f"{self.base_url}/api/v1/invalid", timeout=10)
            success = response.status_code == 404
            self.log_test_result("API 404错误处理", success, 
                               f"状态码: {response.status_code}")
        except Exception as e:
            self.log_test_result("API 404错误处理", False, f"请求失败: {e}")
    
    def test_cors_headers(self):
        """测试CORS头"""
        logger.info("🌐 测试CORS头...")
        
        try:
            response = requests.options(f"{self.base_url}/health", timeout=10)
            headers = response.headers
            
            cors_headers = [
                "Access-Control-Allow-Origin",
                "Access-Control-Allow-Methods",
                "Access-Control-Allow-Headers"
            ]
            
            cors_present = any(header in headers for header in cors_headers)
            self.log_test_result("CORS头设置", cors_present, 
                               f"CORS头存在: {cors_present}")
        except Exception as e:
            self.log_test_result("CORS头设置", False, f"请求失败: {e}")
    
    def generate_report(self):
        """生成测试报告"""
        logger.info("📊 生成测试报告...")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        report = f"""
# BountyGo API端点测试报告

## 测试概览
- **测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **总测试数**: {total_tests}
- **通过测试**: {passed_tests}
- **失败测试**: {failed_tests}
- **成功率**: {(passed_tests/total_tests*100):.1f}%

## 测试结果详情

### ✅ 通过的测试
"""
        
        for result in self.test_results:
            if result["success"]:
                report += f"- **{result['test']}**: {result['details'] or '成功'}\n"
        
        report += "\n### ❌ 失败的测试\n"
        
        for result in self.test_results:
            if not result["success"]:
                report += f"- **{result['test']}**: {result['details'] or '失败'}\n"
        
        report += f"""

## 服务器信息
- **测试URL**: {self.base_url}
- **FastAPI应用**: BountyGo Backend
- **API版本**: v1

## 建议
"""
        
        if failed_tests == 0:
            report += "🎉 所有测试通过！API服务运行正常。\n"
        else:
            report += f"⚠️ 有 {failed_tests} 个测试失败，请检查相关功能。\n"
        
        # 保存报告
        with open("API_TEST_REPORT.md", "w", encoding="utf-8") as f:
            f.write(report)
        
        logger.info("📄 测试报告已生成: API_TEST_REPORT.md")
        
        return passed_tests, total_tests
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("🎯 开始全面API端点测试")
        logger.info("=" * 60)
        
        # 启动服务器
        if not self.start_server():
            logger.error("❌ 无法启动服务器，测试终止")
            return False
        
        try:
            # 运行各种测试
            self.test_basic_endpoints()
            self.test_documentation_endpoints()
            self.test_api_v1_endpoints()
            self.test_error_handling()
            self.test_cors_headers()
            
            # 生成报告
            passed, total = self.generate_report()
            
            # 总结
            logger.info("=" * 60)
            logger.info(f"📊 测试完成: {passed}/{total} 通过")
            
            if passed == total:
                logger.info("🎉 所有API端点测试通过！")
                return True
            else:
                logger.warning(f"⚠️ {total - passed} 个测试失败")
                return False
                
        finally:
            self.stop_server()


def main():
    """主函数"""
    tester = APITester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)