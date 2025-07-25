#!/usr/bin/env python3
"""
简化的API测试脚本
使用subprocess调用curl来避免网络代理问题
"""
import subprocess
import json
import sys
from pathlib import Path

def run_curl(method, url, headers=None, data=None):
    """运行curl命令"""
    cmd = ["curl", "-s", "-w", "\\n%{http_code}"]
    
    if method.upper() != "GET":
        cmd.extend(["-X", method.upper()])
    
    if headers:
        for key, value in headers.items():
            cmd.extend(["-H", f"{key}: {value}"])
    
    if data:
        cmd.extend(["-H", "Content-Type: application/json"])
        cmd.extend(["-d", json.dumps(data)])
    
    cmd.append(url)
    
    try:
        # 使用utf-8编码处理中文响应
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if lines and lines[-1].isdigit():
                status_code = int(lines[-1])
                response_body = '\n'.join(lines[:-1]) if len(lines) > 1 else ""
                return status_code, response_body
            else:
                return None, f"Invalid response format: {result.stdout}"
        else:
            return None, f"curl error: {result.stderr}"
    except Exception as e:
        return None, f"Exception: {e}"

def test_endpoint(name, method, url, headers=None, data=None, expected_status=200):
    """测试单个端点"""
    print(f"🔍 测试: {name}")
    print(f"   请求: {method} {url}")
    
    status_code, response = run_curl(method, url, headers, data)
    
    if status_code is None:
        print(f"   ❌ 请求失败: {response}")
        return False
    
    print(f"   状态码: {status_code}")
    
    if status_code == expected_status:
        print(f"   ✅ 通过")
        if response and len(response) > 100:
            print(f"   响应: {response[:100]}...")
        else:
            print(f"   响应: {response}")
        return True
    else:
        print(f"   ❌ 失败 - 期望状态码: {expected_status}")
        print(f"   响应: {response}")
        return False

def main():
    """主函数"""
    base_url = "http://localhost:8000"
    dev_token = "dev-bountygo-Dsdlr9dYRAlfT0H9VFTF_g-2024"
    auth_headers = {"Authorization": f"Bearer {dev_token}"}
    
    print("🚀 BountyGo API 简化测试")
    print("=" * 50)
    
    tests = [
        # 系统信息
        ("健康检查", "GET", f"{base_url}/health", None, None, 200),
        ("API信息", "GET", f"{base_url}/api/v1/", None, None, 200),
        ("开发认证信息", "GET", f"{base_url}/api/v1/dev-auth", None, None, 200),
        
        # 认证错误测试
        ("无认证头", "GET", f"{base_url}/api/v1/users/me", None, None, 401),
        ("空token", "GET", f"{base_url}/api/v1/users/me", {"Authorization": "Bearer "}, None, 401),
        ("null token", "GET", f"{base_url}/api/v1/users/me", {"Authorization": "Bearer null"}, None, 401),
        
        # 开发token测试
        ("获取当前用户", "GET", f"{base_url}/api/v1/users/me", auth_headers, None, 200),
        ("获取用户钱包", "GET", f"{base_url}/api/v1/users/me/wallets", auth_headers, None, 200),
        
        # 公开端点
        ("任务列表", "GET", f"{base_url}/api/v1/tasks/", None, None, 200),
        ("标签列表", "GET", f"{base_url}/api/v1/tags/", None, None, 200),
        ("标签分类", "GET", f"{base_url}/api/v1/tags/categories", None, None, 200),
        
        # 分析端点
        ("系统统计", "GET", f"{base_url}/api/v1/analytics/system", None, None, 200),
        ("热门标签", "GET", f"{base_url}/api/v1/analytics/popular-tags", None, None, 200),
        ("个人统计", "GET", f"{base_url}/api/v1/analytics/me", auth_headers, None, 200),
        
        # 错误端点
        ("不存在的端点", "GET", f"{base_url}/api/v1/nonexistent", None, None, 404),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_args in tests:
        if test_endpoint(*test_args):
            passed += 1
        print()
    
    print("=" * 50)
    print(f"🎯 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print(f"❌ 有 {total - passed} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())