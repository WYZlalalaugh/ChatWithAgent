#!/usr/bin/env python3
"""
测试运行脚本
提供不同类型测试的便捷运行方式
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """运行命令并输出结果"""
    print(f"\n{'='*60}")
    if description:
        print(f"🚀 {description}")
    print(f"📝 执行命令: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("⚠️ 警告信息:")
            print(result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败 (返回码: {e.returncode})")
        print("标准输出:")
        print(e.stdout)
        print("错误输出:")
        print(e.stderr)
        return False


def run_unit_tests():
    """运行单元测试"""
    cmd = [
        "python", "-m", "pytest", 
        "tests/test_auth.py",
        "tests/test_bots.py", 
        "-v", "--tb=short"
    ]
    return run_command(cmd, "运行单元测试")


def run_integration_tests():
    """运行集成测试"""
    cmd = [
        "python", "-m", "pytest",
        "tests/test_integration.py",
        "-v", "--tb=short", "-s"
    ]
    return run_command(cmd, "运行集成测试")


def run_api_tests():
    """运行API测试"""
    cmd = [
        "python", "-m", "pytest",
        "tests/test_auth.py",
        "tests/test_bots.py",
        "tests/test_conversations.py",
        "tests/test_multimodal.py",
        "tests/test_monitoring.py",
        "-v", "--tb=short"
    ]
    return run_command(cmd, "运行API测试")


def run_performance_tests():
    """运行性能测试"""
    cmd = [
        "python", "-m", "pytest",
        "tests/test_performance.py",
        "-v", "--tb=short", "-s",
        "-m", "performance"
    ]
    return run_command(cmd, "运行性能测试")


def run_smoke_tests():
    """运行冒烟测试"""
    cmd = [
        "python", "-m", "pytest",
        "tests/test_integration.py::test_full_system_smoke_test",
        "-v", "--tb=short", "-s"
    ]
    return run_command(cmd, "运行冒烟测试")


def run_all_tests():
    """运行所有测试"""
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "-v", "--tb=short",
        "--maxfail=5",
        "--durations=10"
    ]
    return run_command(cmd, "运行所有测试")


def run_coverage():
    """运行测试覆盖率分析"""
    # 检查是否安装了coverage
    try:
        subprocess.run(["coverage", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 未安装coverage包，请先安装: pip install coverage")
        return False
    
    # 运行覆盖率测试
    cmd = [
        "coverage", "run", "-m", "pytest",
        "tests/",
        "--tb=short"
    ]
    
    if run_command(cmd, "运行测试覆盖率分析"):
        # 生成覆盖率报告
        print("\n" + "="*60)
        print("📊 生成覆盖率报告")
        print("="*60)
        
        # 命令行报告
        subprocess.run(["coverage", "report", "-m"], check=False)
        
        # HTML报告
        subprocess.run(["coverage", "html"], check=False)
        print("\n✅ HTML覆盖率报告已生成到 htmlcov/ 目录")
        
        return True
    
    return False


def run_specific_test(test_path):
    """运行指定的测试"""
    cmd = [
        "python", "-m", "pytest",
        test_path,
        "-v", "--tb=short", "-s"
    ]
    return run_command(cmd, f"运行指定测试: {test_path}")


def check_test_environment():
    """检查测试环境"""
    print("🔍 检查测试环境...")
    
    # 检查Python版本
    python_version = sys.version_info
    print(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 8):
        print("⚠️ 建议使用Python 3.8或更高版本")
    
    # 检查必要的包
    required_packages = [
        "pytest", "fastapi", "sqlalchemy", "pydantic", "redis", "httpx"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (未安装)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ 缺少依赖包: {', '.join(missing_packages)}")
        print("请安装缺少的包:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    # 检查测试文件
    test_files = [
        "tests/conftest.py",
        "tests/test_auth.py", 
        "tests/test_bots.py",
        "tests/test_conversations.py",
        "tests/test_multimodal.py",
        "tests/test_monitoring.py",
        "tests/test_integration.py",
        "tests/test_performance.py"
    ]
    
    missing_files = []
    
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"✅ {test_file}")
        else:
            print(f"❌ {test_file} (不存在)")
            missing_files.append(test_file)
    
    if missing_files:
        print(f"\n⚠️ 缺少测试文件: {', '.join(missing_files)}")
        return False
    
    print("\n✅ 测试环境检查完成")
    return True


def main():
    parser = argparse.ArgumentParser(description="ChatAgent 测试运行脚本")
    parser.add_argument(
        "test_type", 
        choices=[
            "all", "unit", "integration", "api", "performance", 
            "smoke", "coverage", "check", "specific"
        ],
        help="测试类型"
    )
    parser.add_argument(
        "--path", 
        help="指定测试路径 (用于specific类型)"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true",
        help="详细输出"
    )
    
    args = parser.parse_args()
    
    # 设置工作目录
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print("🤖 ChatAgent 测试运行器")
    print(f"📁 工作目录: {os.getcwd()}")
    
    success = True
    
    if args.test_type == "check":
        success = check_test_environment()
    elif args.test_type == "unit":
        success = run_unit_tests()
    elif args.test_type == "integration":
        success = run_integration_tests()
    elif args.test_type == "api":
        success = run_api_tests()
    elif args.test_type == "performance":
        success = run_performance_tests()
    elif args.test_type == "smoke":
        success = run_smoke_tests()
    elif args.test_type == "coverage":
        success = run_coverage()
    elif args.test_type == "all":
        success = run_all_tests()
    elif args.test_type == "specific":
        if not args.path:
            print("❌ 使用 --path 参数指定测试路径")
            sys.exit(1)
        success = run_specific_test(args.path)
    
    if success:
        print("\n🎉 测试执行完成!")
        sys.exit(0)
    else:
        print("\n💥 测试执行失败!")
        sys.exit(1)


if __name__ == "__main__":
    main()