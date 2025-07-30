#!/usr/bin/env python3
"""
BenchBoard 完整系统测试脚本
测试所有功能：数据存储、API接口、历史数据页面、点击功能等

使用方法:
python3 test_complete_system.py

功能:
1. 测试服务器基本功能
2. 测试数据提交和存储
3. 测试历史数据页面
4. 测试API接口
5. 生成测试报告
"""

import requests
import json
import time
import urllib.parse
import os
import sys
from datetime import datetime
from typing import Dict, List

# 测试配置
SERVER_URL = "http://localhost:8080"
TEST_TEAMS = [
    ("team1", "性能测试组"),
    ("team2", "压力测试组"),
    ("team3", "稳定性测试组")
]

class TestResult:
    """测试结果类"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.details = []
        self.start_time = datetime.now()
    
    def add_success(self, test_name: str, message: str = ""):
        self.passed += 1
        self.details.append(f"✅ {test_name}: {message}")
        print(f"✅ {test_name}: {message}")
    
    def add_failure(self, test_name: str, error: str):
        self.failed += 1
        self.details.append(f"❌ {test_name}: {error}")
        print(f"❌ {test_name}: {error}")
    
    def add_info(self, message: str):
        self.details.append(f"ℹ️  {message}")
        print(f"ℹ️  {message}")
    
    def get_summary(self) -> str:
        total = self.passed + self.failed
        duration = (datetime.now() - self.start_time).total_seconds()
        
        summary = f"""
🧪 测试完成报告
{'='*60}
📊 测试统计:
   - 总测试数: {total}
   - 通过: {self.passed}
   - 失败: {self.failed}
   - 成功率: {(self.passed/total*100):.1f}%
   - 耗时: {duration:.2f}秒

📋 详细结果:
"""
        for detail in self.details:
            summary += f"   {detail}\n"
        
        return summary

def generate_test_data(team_num: int = 1) -> Dict:
    """生成测试数据"""
    base_qps = 8.0 + team_num * 2
    base_latency = 40.0 + team_num * 10
    
    return {
        "totalElapsed": 120.5 + team_num * 30,
        "totalSent": 1000 + team_num * 500,
        "totalOps": 980 + team_num * 450,
        "totalErrors": 20 - team_num * 5,
        "totalSaveDelayErrors": 5,
        "totalAvgLatency": base_latency,
        "highPriorityAvgDelayLatency": base_latency * 0.7,
        "totalVerifyErrorRate": max(0.1, 2.5 - team_num * 0.3),
        "pending": 15 + team_num,
        "operations": {
            "sensorData": {"operations": 500 + team_num * 100, "errors": 10 - team_num}
        },
        "highPriorityStats": {
            "sensorDataCount": 50 + team_num * 10,
            "totalCount": 98 + team_num * 20,
            "percentage": 10.0 + team_num
        },
        "performanceMetrics": {
            "avgSentQPS": base_qps + 0.2,
            "avgCompletedQPS": base_qps,
            "errorRate": max(0.5, 3.0 - team_num * 0.5)
        },
        "latencyAnalysis": {
            "sensorData": {
                "avg": base_latency,
                "min": base_latency * 0.3,
                "max": base_latency * 5,
                "buckets": [100, 200, 150, 80, 50, 20, 10, 5, 2, 1, 0, 0],
                "highPriorityCount": 50 + team_num * 10,
                "highPriorityAvg": base_latency * 0.7,
                "highPriorityMin": base_latency * 0.2,
                "highPriorityMax": base_latency * 3,
                "highPriorityBuckets": [20, 15, 10, 3, 2, 0, 0, 0, 0, 0, 0, 0]
            }
        }
    }

def test_server_connectivity(result: TestResult):
    """测试服务器连接性"""
    result.add_info("开始测试服务器连接性...")
    
    try:
        response = requests.get(f"{SERVER_URL}/", timeout=10)
        if response.status_code == 200:
            result.add_success("服务器连接", f"状态码: {response.status_code}")
        else:
            result.add_failure("服务器连接", f"状态码: {response.status_code}")
    except Exception as e:
        result.add_failure("服务器连接", str(e))

def test_data_submission(result: TestResult):
    """测试数据提交功能"""
    result.add_info("开始测试数据提交功能...")
    
    for i, (team_id, team_name) in enumerate(TEST_TEAMS):
        try:
            url = f"{SERVER_URL}/api/stats/report"
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'Accept-Charset': 'utf-8',
                'X-Team-ID': team_id,
                'X-Team-Name': urllib.parse.quote(team_name)
            }
            
            data = generate_test_data(i + 1)
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                timeout=10
            )
            
            if response.status_code == 200:
                result.add_success(f"数据提交 - {team_name}", "数据提交成功")
            else:
                result.add_failure(f"数据提交 - {team_name}", f"状态码: {response.status_code}")
                
        except Exception as e:
            result.add_failure(f"数据提交 - {team_name}", str(e))
        
        time.sleep(1)  # 避免请求过于频繁

def test_api_endpoints(result: TestResult):
    """测试API接口"""
    result.add_info("开始测试API接口...")
    
    # 测试团队列表API
    try:
        response = requests.get(f"{SERVER_URL}/api/teams", timeout=10)
        if response.status_code == 200:
            teams = response.json()
            result.add_success("团队列表API", f"返回 {len(teams)} 个团队")
        else:
            result.add_failure("团队列表API", f"状态码: {response.status_code}")
    except Exception as e:
        result.add_failure("团队列表API", str(e))
    
    # 测试单个团队API
    for team_id, team_name in TEST_TEAMS:
        try:
            response = requests.get(f"{SERVER_URL}/api/teams/{team_id}", timeout=10)
            if response.status_code == 200:
                team_data = response.json()
                result.add_success(f"团队详情API - {team_name}", "数据获取成功")
            else:
                result.add_failure(f"团队详情API - {team_name}", f"状态码: {response.status_code}")
        except Exception as e:
            result.add_failure(f"团队详情API - {team_name}", str(e))
    
    # 测试历史数据摘要API
    for team_id, team_name in TEST_TEAMS:
        try:
            response = requests.get(f"{SERVER_URL}/api/teams/{team_id}/history/summary", timeout=10)
            if response.status_code == 200:
                summary = response.json()
                total_reports = summary.get('total_reports', 0)
                result.add_success(f"历史摘要API - {team_name}", f"报告数: {total_reports}")
            else:
                result.add_failure(f"历史摘要API - {team_name}", f"状态码: {response.status_code}")
        except Exception as e:
            result.add_failure(f"历史摘要API - {team_name}", str(e))
    
    # 测试历史数据API
    for team_id, team_name in TEST_TEAMS:
        try:
            response = requests.get(f"{SERVER_URL}/api/teams/{team_id}/history?limit=5", timeout=10)
            if response.status_code == 200:
                history = response.json()
                history_count = len(history.get('history', []))
                result.add_success(f"历史数据API - {team_name}", f"返回 {history_count} 条记录")
            else:
                result.add_failure(f"历史数据API - {team_name}", f"状态码: {response.status_code}")
        except Exception as e:
            result.add_failure(f"历史数据API - {team_name}", str(e))

def test_history_pages(result: TestResult):
    """测试历史数据页面"""
    result.add_info("开始测试历史数据页面...")
    
    for team_id, team_name in TEST_TEAMS:
        try:
            response = requests.get(f"{SERVER_URL}/team/{team_id}/history", timeout=10)
            if response.status_code == 200:
                content = response.text
                if "历史数据" in content and team_name in content:
                    result.add_success(f"历史页面 - {team_name}", "页面内容正确")
                else:
                    result.add_failure(f"历史页面 - {team_name}", "页面内容不完整")
            else:
                result.add_failure(f"历史页面 - {team_name}", f"状态码: {response.status_code}")
        except Exception as e:
            result.add_failure(f"历史页面 - {team_name}", str(e))

def test_data_storage(result: TestResult):
    """测试数据存储"""
    result.add_info("开始测试数据存储...")
    
    for team_id, team_name in TEST_TEAMS:
        team_dir = f"data/{team_id}"
        
        # 检查团队目录是否存在
        if os.path.exists(team_dir):
            result.add_success(f"数据目录 - {team_name}", f"目录存在: {team_dir}")
            
            # 检查latest.json是否存在
            latest_file = f"{team_dir}/latest.json"
            if os.path.exists(latest_file):
                result.add_success(f"最新数据文件 - {team_name}", "latest.json存在")
            else:
                result.add_failure(f"最新数据文件 - {team_name}", "latest.json不存在")
            
            # 统计历史文件数量
            json_files = [f for f in os.listdir(team_dir) if f.endswith('.json') and f != 'latest.json']
            result.add_success(f"历史文件数量 - {team_name}", f"{len(json_files)} 个历史文件")
            
        else:
            result.add_failure(f"数据目录 - {team_name}", f"目录不存在: {team_dir}")

def test_multiple_submissions(result: TestResult):
    """测试多次数据提交"""
    result.add_info("开始测试多次数据提交...")
    
    team_id, team_name = TEST_TEAMS[0]  # 使用第一个团队测试
    
    for i in range(3):
        try:
            url = f"{SERVER_URL}/api/stats/report"
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'X-Team-ID': team_id,
                'X-Team-Name': urllib.parse.quote(team_name)
            }
            
            data = generate_test_data(i + 1)
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                timeout=10
            )
            
            if response.status_code == 200:
                result.add_success(f"多次提交 - 第{i+1}次", "提交成功")
            else:
                result.add_failure(f"多次提交 - 第{i+1}次", f"状态码: {response.status_code}")
                
        except Exception as e:
            result.add_failure(f"多次提交 - 第{i+1}次", str(e))
        
        time.sleep(1)

def generate_demo_data(result: TestResult):
    """生成演示数据"""
    result.add_info("生成演示数据...")
    
    # 为每个团队生成多条历史记录
    for round_num in range(1, 4):
        result.add_info(f"生成第 {round_num} 轮演示数据...")
        
        for i, (team_id, team_name) in enumerate(TEST_TEAMS):
            try:
                url = f"{SERVER_URL}/api/stats/report"
                headers = {
                    'Content-Type': 'application/json; charset=utf-8',
                    'X-Team-ID': team_id,
                    'X-Team-Name': urllib.parse.quote(team_name)
                }
                
                # 生成略有变化的数据
                data = generate_test_data(i + round_num)
                response = requests.post(
                    url,
                    headers=headers,
                    data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                    timeout=10
                )
                
                if response.status_code == 200:
                    result.add_success(f"演示数据 - {team_name} 第{round_num}轮", "生成成功")
                else:
                    result.add_failure(f"演示数据 - {team_name} 第{round_num}轮", f"状态码: {response.status_code}")
                    
            except Exception as e:
                result.add_failure(f"演示数据 - {team_name} 第{round_num}轮", str(e))
            
            time.sleep(0.5)  # 短暂延迟确保时间戳不同
        
        time.sleep(1)  # 轮次间延迟

def save_test_report(result: TestResult):
    """保存测试报告"""
    report_content = result.get_summary()
    
    # 保存到文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"test_report_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n📄 测试报告已保存到: {report_file}")
    return report_file

def print_manual_test_guide():
    """打印手动测试指南"""
    print(f"""
🧪 手动测试指南
{'='*60}
完成自动化测试后，请手动验证以下功能：

1. 📊 看板功能测试:
   - 打开: {SERVER_URL}
   - 验证团队卡片是否正确显示
   - 验证实时数据更新

2. 🖱️ 点击功能测试:
   - 鼠标悬停在团队卡片上
   - 验证是否显示"点击查看历史数据"提示
   - 点击任意团队卡片
   - 验证是否在新标签页打开历史数据页面

3. 📈 历史数据页面测试:
   - 验证页面布局和数据显示
   - 测试分页功能（上一页/下一页）
   - 测试排序功能（时间/QPS/延迟排序）
   - 测试导出CSV功能
   - 测试页面大小选择
   - 测试刷新按钮

4. 📱 响应式测试:
   - 在不同屏幕尺寸下测试
   - 验证移动设备兼容性

5. 🔄 实时更新测试:
   - 运行: python3 test_client.py --team-id team1 --team-name "测试组" --interval 10
   - 观察看板实时更新
   - 查看历史数据页面的数据增长

如果所有测试通过，系统功能正常！🎉
""")

def main():
    """主测试函数"""
    print("🧪 BenchBoard 完整系统测试")
    print("=" * 60)
    
    result = TestResult()
    
    # 执行所有测试
    test_server_connectivity(result)
    generate_demo_data(result)
    test_data_submission(result)
    test_multiple_submissions(result)
    test_api_endpoints(result)
    test_history_pages(result)
    test_data_storage(result)
    
    # 输出测试总结
    print(result.get_summary())
    
    # 保存测试报告
    report_file = save_test_report(result)
    
    # 打印手动测试指南
    print_manual_test_guide()
    
    # 最终状态
    if result.failed == 0:
        print("🎉 所有自动化测试通过！系统功能正常！")
        return 0
    else:
        print(f"⚠️  有 {result.failed} 项测试失败，请检查系统状态！")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 