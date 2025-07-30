#!/usr/bin/env python3
"""
API 接口专项测试脚本
专门测试所有API接口的功能和性能

使用方法:
python3 test_api_endpoints.py

功能:
- 测试所有API接口
- 性能基准测试
- 错误处理测试
- 边界条件测试
"""

import requests
import json
import time
import urllib.parse
from datetime import datetime
from typing import Dict, List

# 测试配置
SERVER_URL = "http://localhost:8080"

class APITester:
    """API测试类"""
    
    def __init__(self):
        self.results = []
        self.start_time = datetime.now()
    
    def log_result(self, test_name: str, success: bool, response_time: float, details: str = ""):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "response_time": response_time,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {response_time:.3f}s - {details}")
    
    def test_endpoint(self, method: str, endpoint: str, data: Dict = None, headers: Dict = None) -> tuple:
        """测试单个端点"""
        url = f"{SERVER_URL}{endpoint}"
        start_time = time.time()
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, data=data, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response_time = time.time() - start_time
            return True, response_time, response.status_code, response
            
        except Exception as e:
            response_time = time.time() - start_time
            return False, response_time, 0, str(e)
    
    def test_main_dashboard(self):
        """测试主看板页面"""
        print("\n🏠 测试主看板页面")
        
        success, response_time, status_code, response = self.test_endpoint("GET", "/")
        
        if success and status_code == 200:
            content_length = len(response.text)
            self.log_result("主看板页面", True, response_time, f"状态码:{status_code}, 内容长度:{content_length}")
        else:
            self.log_result("主看板页面", False, response_time, f"状态码:{status_code}")
    
    def test_stats_submission(self):
        """测试数据提交接口"""
        print("\n📊 测试数据提交接口")
        
        # 测试数据
        test_data = {
            "totalElapsed": 120.5,
            "totalSent": 1000,
            "totalOps": 980,
            "totalErrors": 20,
            "totalSaveDelayErrors": 5,
            "totalAvgLatency": 45.2,
            "highPriorityAvgDelayLatency": 32.1,
            "totalVerifyErrorRate": 1.8,
            "pending": 15,
            "operations": {
                "sensorData": {"operations": 500, "errors": 10}
            },
            "highPriorityStats": {
                "sensorDataCount": 50,
                "totalCount": 98,
                "percentage": 10.0
            },
            "performanceMetrics": {
                "avgSentQPS": 8.3,
                "avgCompletedQPS": 8.1,
                "errorRate": 2.0
            },
            "latencyAnalysis": {
                "sensorData": {
                    "avg": 45.2,
                    "min": 12.1,
                    "max": 234.5,
                    "buckets": [100, 200, 150, 80, 50, 20, 10, 5, 2, 1, 0, 0],
                    "highPriorityCount": 50,
                    "highPriorityAvg": 32.1,
                    "highPriorityMin": 8.5,
                    "highPriorityMax": 156.2,
                    "highPriorityBuckets": [20, 15, 10, 3, 2, 0, 0, 0, 0, 0, 0, 0]
                }
            }
        }
        
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Accept-Charset': 'utf-8',
            'X-Team-ID': 'test_team',
            'X-Team-Name': urllib.parse.quote('API测试组')
        }
        
        data_str = json.dumps(test_data, ensure_ascii=False).encode('utf-8')
        
        success, response_time, status_code, response = self.test_endpoint(
            "POST", "/api/stats/report", data=data_str, headers=headers
        )
        
        if success and status_code == 200:
            self.log_result("数据提交接口", True, response_time, f"状态码:{status_code}")
        else:
            self.log_result("数据提交接口", False, response_time, f"状态码:{status_code}")
    
    def test_teams_api(self):
        """测试团队相关API"""
        print("\n👥 测试团队API")
        
        # 测试团队列表API
        success, response_time, status_code, response = self.test_endpoint("GET", "/api/teams")
        
        if success and status_code == 200:
            teams = response.json()
            team_count = len(teams)
            self.log_result("团队列表API", True, response_time, f"返回{team_count}个团队")
            
            # 如果有团队，测试单个团队API
            if teams:
                team_id = teams[0]['team_id']
                
                # 测试团队详情API
                success2, response_time2, status_code2, response2 = self.test_endpoint(
                    "GET", f"/api/teams/{team_id}"
                )
                
                if success2 and status_code2 == 200:
                    self.log_result("团队详情API", True, response_time2, f"团队ID:{team_id}")
                else:
                    self.log_result("团队详情API", False, response_time2, f"状态码:{status_code2}")
        else:
            self.log_result("团队列表API", False, response_time, f"状态码:{status_code}")
    
    def test_history_api(self):
        """测试历史数据API"""
        print("\n📈 测试历史数据API")
        
        test_team_id = "test_team"
        
        # 测试历史数据摘要API
        success, response_time, status_code, response = self.test_endpoint(
            "GET", f"/api/teams/{test_team_id}/history/summary"
        )
        
        if success and status_code == 200:
            summary = response.json()
            report_count = summary.get('total_reports', 0)
            self.log_result("历史摘要API", True, response_time, f"报告数:{report_count}")
        else:
            self.log_result("历史摘要API", False, response_time, f"状态码:{status_code}")
        
        # 测试历史数据API（默认参数）
        success, response_time, status_code, response = self.test_endpoint(
            "GET", f"/api/teams/{test_team_id}/history"
        )
        
        if success and status_code == 200:
            history = response.json()
            history_count = len(history.get('history', []))
            self.log_result("历史数据API（默认）", True, response_time, f"返回{history_count}条记录")
        else:
            self.log_result("历史数据API（默认）", False, response_time, f"状态码:{status_code}")
        
        # 测试历史数据API（自定义参数）
        success, response_time, status_code, response = self.test_endpoint(
            "GET", f"/api/teams/{test_team_id}/history?limit=5&offset=0"
        )
        
        if success and status_code == 200:
            history = response.json()
            history_count = len(history.get('history', []))
            has_more = history.get('has_more', False)
            self.log_result("历史数据API（分页）", True, response_time, 
                          f"返回{history_count}条记录, 有更多:{has_more}")
        else:
            self.log_result("历史数据API（分页）", False, response_time, f"状态码:{status_code}")
    
    def test_history_pages(self):
        """测试历史数据页面"""
        print("\n🌐 测试历史数据页面")
        
        test_team_id = "test_team"
        
        success, response_time, status_code, response = self.test_endpoint(
            "GET", f"/team/{test_team_id}/history"
        )
        
        if success and status_code == 200:
            content = response.text
            has_required_content = "历史数据" in content and "API测试组" in content
            content_length = len(content)
            
            if has_required_content:
                self.log_result("历史数据页面", True, response_time, 
                              f"内容长度:{content_length}, 包含必要元素")
            else:
                self.log_result("历史数据页面", False, response_time, 
                              f"内容长度:{content_length}, 缺少必要元素")
        else:
            self.log_result("历史数据页面", False, response_time, f"状态码:{status_code}")
    
    def test_error_handling(self):
        """测试错误处理"""
        print("\n⚠️ 测试错误处理")
        
        # 测试不存在的团队
        success, response_time, status_code, response = self.test_endpoint(
            "GET", "/api/teams/nonexistent_team"
        )
        
        if status_code == 404:
            self.log_result("不存在团队(404)", True, response_time, "正确返回404")
        else:
            self.log_result("不存在团队(404)", False, response_time, f"期望404，实际{status_code}")
        
        # 测试不存在的历史数据
        success, response_time, status_code, response = self.test_endpoint(
            "GET", "/api/teams/nonexistent_team/history"
        )
        
        if status_code in [200, 404]:  # 可能返回空数据或404
            self.log_result("不存在历史数据", True, response_time, f"状态码:{status_code}")
        else:
            self.log_result("不存在历史数据", False, response_time, f"状态码:{status_code}")
        
        # 测试无效的数据提交（缺少必要字段）
        invalid_data = {"invalid": "data"}
        headers = {
            'Content-Type': 'application/json',
            'X-Team-ID': 'test_team',
            'X-Team-Name': 'Test Team'
        }
        
        success, response_time, status_code, response = self.test_endpoint(
            "POST", "/api/stats/report", 
            data=json.dumps(invalid_data).encode('utf-8'), 
            headers=headers
        )
        
        if status_code == 400:
            self.log_result("无效数据提交(400)", True, response_time, "正确返回400")
        else:
            self.log_result("无效数据提交(400)", False, response_time, f"期望400，实际{status_code}")
    
    def test_performance_benchmark(self):
        """性能基准测试"""
        print("\n⚡ 性能基准测试")
        
        # 测试多次快速请求
        response_times = []
        
        for i in range(10):
            success, response_time, status_code, response = self.test_endpoint("GET", "/api/teams")
            if success and status_code == 200:
                response_times.append(response_time)
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            self.log_result("API性能基准", True, avg_time, 
                          f"平均:{avg_time:.3f}s, 最大:{max_time:.3f}s, 最小:{min_time:.3f}s")
        else:
            self.log_result("API性能基准", False, 0, "所有请求失败")
    
    def test_concurrent_requests(self):
        """并发请求测试"""
        print("\n🔄 并发请求测试")
        
        import threading
        
        results = []
        
        def make_request():
            success, response_time, status_code, response = self.test_endpoint("GET", "/api/teams")
            results.append((success, response_time, status_code))
        
        # 创建5个并发线程
        threads = []
        start_time = time.time()
        
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        success_count = sum(1 for success, _, status in results if success and status == 200)
        
        self.log_result("并发请求测试", success_count == 5, total_time, 
                       f"成功:{success_count}/5, 总时间:{total_time:.3f}s")
    
    def generate_report(self):
        """生成测试报告"""
        total_tests = len(self.results)
        successful_tests = sum(1 for result in self.results if result["success"])
        failed_tests = total_tests - successful_tests
        
        total_time = (datetime.now() - self.start_time).total_seconds()
        avg_response_time = sum(result["response_time"] for result in self.results) / total_tests if total_tests > 0 else 0
        
        report = f"""
🧪 API测试完成报告
{'='*60}
📊 测试统计:
   - 总测试数: {total_tests}
   - 成功: {successful_tests}
   - 失败: {failed_tests}
   - 成功率: {(successful_tests/total_tests*100):.1f}%
   - 总耗时: {total_time:.2f}秒
   - 平均响应时间: {avg_response_time:.3f}秒

📋 详细结果:
"""
        
        for result in self.results:
            status = "✅" if result["success"] else "❌"
            report += f"   {status} {result['test_name']}: {result['response_time']:.3f}s - {result['details']}\n"
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"api_test_report_{timestamp}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(report)
        print(f"📄 测试报告已保存到: {report_file}")
        
        return successful_tests == total_tests
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始API接口专项测试")
        print("="*60)
        
        # 运行所有测试
        self.test_main_dashboard()
        self.test_stats_submission()
        self.test_teams_api()
        self.test_history_api()
        self.test_history_pages()
        self.test_error_handling()
        self.test_performance_benchmark()
        self.test_concurrent_requests()
        
        # 生成报告
        print("\n" + "="*60)
        success = self.generate_report()
        
        if success:
            print("🎉 所有API测试通过！")
        else:
            print("⚠️ 部分API测试失败！")
        
        return success

def main():
    """主函数"""
    # 检查服务器连接
    try:
        response = requests.get(f"{SERVER_URL}/", timeout=5)
        if response.status_code != 200:
            print(f"❌ 服务器连接失败: {SERVER_URL}")
            print("请确保运行: python3 app.py")
            return 1
    except Exception as e:
        print(f"❌ 无法连接服务器: {e}")
        print("请确保运行: python3 app.py")
        return 1
    
    # 运行测试
    tester = APITester()
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main()) 