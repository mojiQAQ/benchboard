#!/usr/bin/env python3
"""
实时演示测试脚本
模拟多个团队持续上报数据，用于测试实时更新功能

使用方法:
python3 test_realtime_demo.py [--duration 60] [--interval 5]

功能:
- 3个团队持续上报数据
- 模拟不同的性能表现
- 可配置运行时长和上报间隔
- 实时显示上报状态
"""

import requests
import json
import time
import urllib.parse
import argparse
import threading
import random
from datetime import datetime
from typing import Dict

# 服务器配置
SERVER_URL = "http://localhost:8080"

# 团队配置
TEAMS = [
    {
        "id": "team1",
        "name": "性能测试组",
        "base_qps": 12.0,
        "base_latency": 35.0,
        "performance_trend": "improving"  # improving, declining, stable
    },
    {
        "id": "team2", 
        "name": "压力测试组",
        "base_qps": 8.5,
        "base_latency": 55.0,
        "performance_trend": "stable"
    },
    {
        "id": "team3",
        "name": "稳定性测试组", 
        "base_qps": 15.2,
        "base_latency": 28.0,
        "performance_trend": "declining"
    }
]

class RealtimeDemo:
    """实时演示类"""
    
    def __init__(self, duration: int = 60, interval: int = 5):
        self.duration = duration
        self.interval = interval
        self.running = True
        self.submission_count = 0
        self.success_count = 0
        self.error_count = 0
        self.start_time = datetime.now()
        
    def generate_dynamic_data(self, team: Dict, round_num: int) -> Dict:
        """根据团队配置和轮次生成动态数据"""
        
        # 基础性能指标
        base_qps = team["base_qps"]
        base_latency = team["base_latency"]
        
        # 根据性能趋势调整数据
        trend = team["performance_trend"]
        if trend == "improving":
            qps_multiplier = 1.0 + (round_num * 0.05)  # QPS逐渐提升
            latency_multiplier = 1.0 - (round_num * 0.02)  # 延迟逐渐降低
        elif trend == "declining":
            qps_multiplier = 1.0 - (round_num * 0.03)  # QPS逐渐下降
            latency_multiplier = 1.0 + (round_num * 0.04)  # 延迟逐渐增加
        else:  # stable
            qps_multiplier = 1.0 + random.uniform(-0.1, 0.1)  # 小幅波动
            latency_multiplier = 1.0 + random.uniform(-0.05, 0.05)
        
        # 添加随机波动
        qps_variation = random.uniform(0.8, 1.2)
        latency_variation = random.uniform(0.9, 1.1)
        
        current_qps = base_qps * qps_multiplier * qps_variation
        current_latency = base_latency * latency_multiplier * latency_variation
        
        # 确保数值在合理范围内
        current_qps = max(1.0, min(50.0, current_qps))
        current_latency = max(10.0, min(200.0, current_latency))
        
        # 根据性能计算其他指标
        error_rate = max(0.1, 8.0 - current_qps * 0.3)  # QPS越高错误率越低
        total_requests = int(current_qps * 120)  # 假设运行2分钟
        error_count = int(total_requests * error_rate / 100)
        
        return {
            "totalElapsed": 120.0 + random.uniform(-10, 10),
            "totalSent": total_requests + random.randint(-50, 50),
            "totalOps": total_requests - error_count,
            "totalErrors": error_count,
            "totalSaveDelayErrors": random.randint(0, 5),
            "totalAvgLatency": current_latency,
            "highPriorityAvgDelayLatency": current_latency * 0.7,
            "totalVerifyErrorRate": max(0.1, 5.0 - current_qps * 0.15),
            "pending": random.randint(5, 25),
            "operations": {
                "sensorData": {
                    "operations": int(total_requests * 0.5),
                    "errors": int(error_count * 0.6)
                },
                "sensorRW": {
                    "operations": int(total_requests * 0.25),
                    "errors": int(error_count * 0.2)
                },
                "batchRW": {
                    "operations": int(total_requests * 0.15),
                    "errors": int(error_count * 0.15)
                },
                "query": {
                    "operations": int(total_requests * 0.1),
                    "errors": int(error_count * 0.05)
                }
            },
            "highPriorityStats": {
                "sensorDataCount": random.randint(40, 80),
                "sensorRWCount": random.randint(15, 35),
                "batchRWCount": random.randint(10, 25),
                "queryCount": random.randint(8, 20),
                "totalCount": random.randint(80, 150),
                "percentage": random.uniform(8.0, 15.0)
            },
            "performanceMetrics": {
                "avgSentQPS": current_qps + random.uniform(-0.5, 0.5),
                "avgCompletedQPS": current_qps,
                "errorRate": error_rate
            },
            "latencyAnalysis": {
                "sensorData": {
                    "avg": current_latency,
                    "min": current_latency * 0.3,
                    "max": current_latency * 4,
                    "buckets": self.generate_latency_buckets(current_latency),
                    "highPriorityCount": random.randint(40, 70),
                    "highPriorityAvg": current_latency * 0.7,
                    "highPriorityMin": current_latency * 0.2,
                    "highPriorityMax": current_latency * 2.5,
                    "highPriorityBuckets": self.generate_latency_buckets(current_latency * 0.7, True)
                },
                "sensorRW": {
                    "avg": current_latency + 15,
                    "min": current_latency * 0.4,
                    "max": current_latency * 3.5,
                    "buckets": self.generate_latency_buckets(current_latency + 15)
                },
                "batchRW": {
                    "avg": current_latency + 40,
                    "min": current_latency * 0.8,
                    "max": current_latency * 6,
                    "buckets": self.generate_latency_buckets(current_latency + 40)
                },
                "query": {
                    "avg": current_latency - 8,
                    "min": current_latency * 0.25,
                    "max": current_latency * 2.8,
                    "buckets": self.generate_latency_buckets(current_latency - 8)
                }
            }
        }
    
    def generate_latency_buckets(self, avg_latency: float, is_high_priority: bool = False) -> list:
        """根据平均延迟生成延迟分布桶"""
        # 简化的延迟分布生成
        base_total = 500 if not is_high_priority else 50
        
        # 根据平均延迟决定分布
        if avg_latency < 30:
            # 低延迟分布，大部分在前几个桶
            return [
                int(base_total * 0.4), int(base_total * 0.3), int(base_total * 0.15),
                int(base_total * 0.08), int(base_total * 0.04), int(base_total * 0.02),
                int(base_total * 0.01), 0, 0, 0, 0, 0
            ]
        elif avg_latency < 60:
            # 中等延迟分布
            return [
                int(base_total * 0.2), int(base_total * 0.25), int(base_total * 0.2),
                int(base_total * 0.15), int(base_total * 0.1), int(base_total * 0.06),
                int(base_total * 0.03), int(base_total * 0.01), 0, 0, 0, 0
            ]
        else:
            # 高延迟分布，更分散
            return [
                int(base_total * 0.1), int(base_total * 0.15), int(base_total * 0.18),
                int(base_total * 0.15), int(base_total * 0.12), int(base_total * 0.1),
                int(base_total * 0.08), int(base_total * 0.06), int(base_total * 0.04),
                int(base_total * 0.02), 0, 0
            ]
    
    def submit_team_data(self, team: Dict, round_num: int) -> bool:
        """提交团队数据"""
        try:
            url = f"{SERVER_URL}/api/stats/report"
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'Accept-Charset': 'utf-8',
                'X-Team-ID': team["id"],
                'X-Team-Name': urllib.parse.quote(team["name"])
            }
            
            data = self.generate_dynamic_data(team, round_num)
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                timeout=10
            )
            
            if response.status_code == 200:
                self.success_count += 1
                return True
            else:
                self.error_count += 1
                return False
                
        except Exception:
            self.error_count += 1
            return False
    
    def print_status(self, round_num: int):
        """打印当前状态"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        remaining = max(0, self.duration - elapsed)
        
        print(f"\r🔄 第{round_num}轮 | "
              f"⏱️ {elapsed:.0f}s/{self.duration}s | "
              f"📊 成功:{self.success_count} 失败:{self.error_count} | "
              f"⏳ 剩余:{remaining:.0f}s", end="", flush=True)
    
    def run_team_simulation(self, team: Dict):
        """运行单个团队的模拟"""
        round_num = 0
        
        while self.running:
            round_num += 1
            success = self.submit_team_data(team, round_num)
            self.submission_count += 1
            
            # 打印状态（只有第一个团队打印，避免重复）
            if team["id"] == "team1":
                self.print_status(round_num)
            
            # 检查是否超时
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed >= self.duration:
                self.running = False
                break
            
            # 等待下次提交
            time.sleep(self.interval)
    
    def run(self):
        """运行演示"""
        print(f"🚀 启动实时演示")
        print(f"📊 配置: 持续时间={self.duration}秒, 上报间隔={self.interval}秒")
        print(f"👥 团队: {len(TEAMS)}个")
        print("="*60)
        
        # 启动多线程模拟
        threads = []
        for team in TEAMS:
            thread = threading.Thread(target=self.run_team_simulation, args=(team,))
            thread.start()
            threads.append(thread)
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 打印最终结果
        print(f"\n\n🎉 演示完成！")
        print(f"📊 统计结果:")
        print(f"   - 总提交次数: {self.submission_count}")
        print(f"   - 成功次数: {self.success_count}")
        print(f"   - 失败次数: {self.error_count}")
        print(f"   - 成功率: {(self.success_count/self.submission_count*100):.1f}%")
        print(f"   - 实际运行时间: {(datetime.now() - self.start_time).total_seconds():.1f}秒")
        
        print(f"\n💡 现在可以:")
        print(f"   1. 访问 {SERVER_URL} 查看实时看板")
        print(f"   2. 点击团队卡片查看历史数据")
        print(f"   3. 观察不同团队的性能趋势")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="BenchBoard实时演示测试")
    parser.add_argument("--duration", type=int, default=60, help="运行持续时间（秒），默认60秒")
    parser.add_argument("--interval", type=int, default=5, help="上报间隔（秒），默认5秒")
    
    args = parser.parse_args()
    
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
    
    # 运行演示
    demo = RealtimeDemo(duration=args.duration, interval=args.interval)
    demo.run()
    
    return 0

if __name__ == "__main__":
    exit(main()) 