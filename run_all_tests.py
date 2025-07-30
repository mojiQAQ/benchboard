#!/usr/bin/env python3
"""
BenchBoard 测试套件
运行所有测试脚本并生成汇总报告

使用方法:
python3 run_all_tests.py [--quick]

功能:
- 运行完整系统测试
- 运行API接口测试 
- 运行实时演示测试
- 生成汇总测试报告
- 提供手动测试指南
"""

import subprocess
import sys
import time
import argparse
from datetime import datetime

class TestSuite:
    """测试套件类"""
    
    def __init__(self, quick_mode: bool = False):
        self.quick_mode = quick_mode
        self.results = []
        self.start_time = datetime.now()
    
    def run_test_script(self, script_name: str, args: list = None) -> dict:
        """运行测试脚本"""
        print(f"\n🧪 运行 {script_name}...")
        print("-" * 60)
        
        cmd = [sys.executable, script_name]
        if args:
            cmd.extend(args)
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            duration = time.time() - start_time
            success = result.returncode == 0
            
            # 打印输出
            if result.stdout:
                print(result.stdout)
            
            if result.stderr and not success:
                print(f"❌ 错误输出:\n{result.stderr}")
            
            return {
                "script": script_name,
                "success": success,
                "duration": duration,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ 执行失败: {e}")
            
            return {
                "script": script_name,
                "success": False,
                "duration": duration,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e)
            }
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 BenchBoard 测试套件")
        print("=" * 60)
        print(f"⏰ 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🚀 模式: {'快速测试' if self.quick_mode else '完整测试'}")
        print("=" * 60)
        
        # 1. 完整系统测试
        result1 = self.run_test_script("test_complete_system.py")
        self.results.append(result1)
        
        # 2. API接口测试
        result2 = self.run_test_script("test_api_endpoints.py")
        self.results.append(result2)
        
        # 3. 实时演示测试
        if self.quick_mode:
            # 快速模式：短时间测试
            result3 = self.run_test_script("test_realtime_demo.py", ["--duration", "15", "--interval", "2"])
        else:
            # 完整模式：标准时间测试
            result3 = self.run_test_script("test_realtime_demo.py", ["--duration", "30", "--interval", "3"])
        self.results.append(result3)
    
    def generate_summary_report(self):
        """生成汇总报告"""
        total_duration = (datetime.now() - self.start_time).total_seconds()
        
        successful_tests = sum(1 for result in self.results if result["success"])
        failed_tests = len(self.results) - successful_tests
        
        report = f"""
🧪 BenchBoard 测试套件汇总报告
{'='*80}
⏰ 测试时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} 
🚀 测试模式: {'快速测试' if self.quick_mode else '完整测试'}
⏱️ 总耗时: {total_duration:.1f}秒

📊 测试统计:
   - 总测试脚本: {len(self.results)}个
   - 成功: {successful_tests}个
   - 失败: {failed_tests}个
   - 成功率: {(successful_tests/len(self.results)*100):.1f}%

📋 详细结果:
"""
        
        for i, result in enumerate(self.results, 1):
            status = "✅" if result["success"] else "❌"
            report += f"   {i}. {status} {result['script']}: {result['duration']:.1f}s (退出码: {result['returncode']})\n"
        
        # 添加性能分析
        if all(result["success"] for result in self.results):
            report += f"""
🎯 性能分析:
   - 最快脚本: {min(self.results, key=lambda x: x['duration'])['script']} ({min(result['duration'] for result in self.results):.1f}s)
   - 最慢脚本: {max(self.results, key=lambda x: x['duration'])['script']} ({max(result['duration'] for result in self.results):.1f}s)
   - 平均耗时: {sum(result['duration'] for result in self.results)/len(self.results):.1f}s

✅ 系统状态: 所有测试通过，系统功能正常！
"""
        else:
            failed_scripts = [result['script'] for result in self.results if not result['success']]
            report += f"""
⚠️ 系统状态: 部分测试失败

❌ 失败的脚本:
"""
            for script in failed_scripts:
                report += f"   - {script}\n"
        
        # 添加手动测试指南
        report += f"""
🧪 手动测试指南:
{'='*60}
自动化测试完成后，请执行以下手动验证:

1. 📊 看板功能验证:
   - 打开: http://localhost:8080
   - 验证3个团队卡片正确显示
   - 验证实时数据正在更新
   - 验证性能指标显示正确

2. 🖱️ 交互功能验证:
   - 鼠标悬停在团队卡片上，观察悬停效果
   - 验证显示"📊 点击查看历史数据"提示
   - 点击任意团队卡片
   - 验证新标签页正确打开历史数据页面

3. 📈 历史数据页面验证:
   - 验证页面标题和团队名称正确
   - 验证数据摘要卡片显示
   - 验证历史数据表格显示
   - 测试分页功能（如有多页数据）
   - 测试排序功能（时间/QPS/延迟）
   - 测试页面大小选择
   - 测试导出CSV功能
   - 测试刷新按钮

4. 📱 响应式测试:
   - 调整浏览器窗口大小
   - 验证在不同尺寸下的显示效果
   - 如有移动设备，在移动设备上测试

5. 🔄 数据存储验证:
   - 检查 data/ 目录结构
   - 验证每个团队都有独立子目录
   - 验证历史文件按时间戳命名
   - 验证 latest.json 文件存在

如果所有测试通过，BenchBoard系统完全正常！🎉

💡 提示:
- 可以运行 `python3 test_realtime_demo.py` 模拟持续数据流
- 可以运行 `python3 test_client.py` 手动发送测试数据
- 服务器日志可以通过控制台查看
"""
        
        return report
    
    def save_report(self, report: str):
        """保存测试报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"test_suite_report_{timestamp}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 测试套件报告已保存到: {report_file}")
        return report_file
    
    def run(self):
        """运行测试套件"""
        # 运行所有测试
        self.run_all_tests()
        
        # 生成和显示报告
        print("\n" + "="*80)
        report = self.generate_summary_report()
        print(report)
        
        # 保存报告
        self.save_report(report)
        
        # 返回结果
        success = all(result["success"] for result in self.results)
        
        if success:
            print("🎉 测试套件执行完成 - 所有测试通过！")
            return 0
        else:
            print("⚠️ 测试套件执行完成 - 部分测试失败！")
            return 1

def check_prerequisites():
    """检查前置条件"""
    import requests
    
    print("🔍 检查前置条件...")
    
    # 检查服务器连接
    try:
        response = requests.get("http://localhost:8080/", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器运行正常")
            return True
        else:
            print(f"❌ 服务器响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接服务器: {e}")
        print("请确保运行: python3 app.py")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="BenchBoard测试套件")
    parser.add_argument("--quick", action="store_true", help="快速测试模式（缩短测试时间）")
    
    args = parser.parse_args()
    
    # 检查前置条件
    if not check_prerequisites():
        return 1
    
    # 运行测试套件
    suite = TestSuite(quick_mode=args.quick)
    return suite.run()

if __name__ == "__main__":
    sys.exit(main()) 