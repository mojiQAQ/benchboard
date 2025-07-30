#!/usr/bin/env python3
"""
测试客户端 - 模拟压测工具上报数据
使用方法：
python test_client.py --team-id team1 --team-name "第一小组"
"""

import requests
import json
import time
import random
import argparse
from datetime import datetime
import sys
import io
import urllib.parse

# 修复终端输出编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def generate_mock_stats():
    """生成模拟的压测统计数据"""
    
    # 基础数据
    total_sent = random.randint(1000, 10000)
    total_ops = int(total_sent * random.uniform(0.85, 0.98))
    total_errors = total_sent - total_ops
    total_save_delay_errors = int(total_errors * random.uniform(0.1, 0.3))
    pending = random.randint(0, 100)
    total_elapsed = random.uniform(30, 300)  # 30秒到5分钟
    
    # 操作统计
    operations = {
        "sensorData": {
            "operations": int(total_ops * random.uniform(0.3, 0.5)),
            "errors": int(total_errors * random.uniform(0.2, 0.4))
        },
        "sensorRW": {
            "operations": int(total_ops * random.uniform(0.2, 0.3)),
            "errors": int(total_errors * random.uniform(0.1, 0.3))
        },
        "batchRW": {
            "operations": int(total_ops * random.uniform(0.1, 0.2)),
            "errors": int(total_errors * random.uniform(0.1, 0.2))
        },
        "query": {
            "operations": int(total_ops * random.uniform(0.1, 0.2)),
            "errors": int(total_errors * random.uniform(0.1, 0.2))
        }
    }
    
    # 高优先级统计
    high_priority_total = int(total_sent * random.uniform(0.1, 0.3))
    high_priority_stats = {
        "sensorDataCount": int(high_priority_total * random.uniform(0.3, 0.5)),
        "sensorRWCount": int(high_priority_total * random.uniform(0.2, 0.3)),
        "batchRWCount": int(high_priority_total * random.uniform(0.1, 0.2)),
        "queryCount": int(high_priority_total * random.uniform(0.1, 0.2)),
        "totalCount": high_priority_total,
        "percentage": (high_priority_total / total_sent) * 100
    }
    
    # 性能指标
    performance_metrics = {
        "avgSentQPS": total_sent / total_elapsed,
        "avgCompletedQPS": total_ops / total_elapsed,
        "errorRate": (total_errors / total_ops) * 100 if total_ops > 0 else 0
    }
    
    # 延迟分析
    def generate_latency_distribution():
        avg_latency = random.uniform(10, 500)
        min_latency = avg_latency * random.uniform(0.1, 0.5)
        max_latency = avg_latency * random.uniform(2, 10)
        
        # 生成延迟分布桶
        buckets = [random.randint(0, 100) for _ in range(13)]  # 13个桶
        
        # 高优先级延迟统计
        high_priority_count = random.randint(0, 100)
        high_priority_avg = avg_latency * random.uniform(0.5, 1.5) if high_priority_count > 0 else None
        high_priority_min = min_latency * random.uniform(0.5, 1.0) if high_priority_count > 0 else None
        high_priority_max = max_latency * random.uniform(0.5, 1.5) if high_priority_count > 0 else None
        high_priority_buckets = [random.randint(0, 50) for _ in range(13)] if high_priority_count > 0 else None
        
        return {
            "avg": avg_latency,
            "min": min_latency,
            "max": max_latency,
            "buckets": buckets,
            "highPriorityCount": high_priority_count,
            "highPriorityAvg": high_priority_avg,
            "highPriorityMin": high_priority_min,
            "highPriorityMax": high_priority_max,
            "highPriorityBuckets": high_priority_buckets
        }
    
    latency_analysis = {
        "sensorData": generate_latency_distribution(),
        "sensorRW": generate_latency_distribution(),
        "batchRW": generate_latency_distribution(),
        "query": generate_latency_distribution()
    }
    
    return {
        "totalElapsed": total_elapsed,
        "totalSent": total_sent,
        "totalOps": total_ops,
        "totalErrors": total_errors,
        "totalSaveDelayErrors": total_save_delay_errors,
        "pending": pending,
        "operations": operations,
        "highPriorityStats": high_priority_stats,
        "performanceMetrics": performance_metrics,
        "latencyAnalysis": latency_analysis
    }

def submit_stats(server_url, team_id, team_name, stats):
    """提交统计数据到服务器"""
    # 对中文团队名进行URL编码，避免HTTP头部编码问题
    encoded_team_name = urllib.parse.quote(team_name, safe='')
    
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Accept-Charset': 'utf-8',
        'X-Team-ID': team_id,
        'X-Team-Name': encoded_team_name
    }
    
    try:
        url = f"{server_url}/api/stats/report"
        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(stats, ensure_ascii=False).encode('utf-8'),
            timeout=10
        )
        if response.status_code == 200:
            print(f"✅ 数据提交成功: {response.json()}")
            return True
        else:
            print(f"❌ 数据提交失败: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络错误: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='BenchBoard 测试客户端')
    parser.add_argument('--team-id', required=True, help='团队ID')
    parser.add_argument('--team-name', required=True, help='团队名称')
    parser.add_argument('--server', default='http://localhost:8080', help='服务器地址')
    parser.add_argument('--interval', type=int, default=30, help='上报间隔（秒）')
    parser.add_argument('--count', type=int, default=0, help='上报次数（0表示无限循环）')
    
    args = parser.parse_args()
    
    print(f"🚀 启动测试客户端")
    print(f"   团队ID: {args.team_id}")
    print(f"   团队名称: {args.team_name}")
    print(f"   服务器地址: {args.server}")
    print(f"   上报间隔: {args.interval}秒")
    print(f"   上报次数: {'无限循环' if args.count == 0 else args.count}")
    print("-" * 50)
    
    count = 0
    while True:
        count += 1
        print(f"\n📊 第 {count} 次上报 - {datetime.now().strftime('%H:%M:%S')}")
        
        # 生成模拟数据
        stats = generate_mock_stats()
        
        # 提交数据
        success = submit_stats(args.server, args.team_id, args.team_name, stats)
        
        if success:
            print(f"   总运行时间: {stats['totalElapsed']:.1f}s")
            print(f"   发送请求: {stats['totalSent']}")
            print(f"   完成请求: {stats['totalOps']}")
            print(f"   错误数: {stats['totalErrors']}")
            print(f"   平均QPS: {stats['performanceMetrics']['avgCompletedQPS']:.1f}")
            print(f"   错误率: {stats['performanceMetrics']['errorRate']:.2f}%")
        
        # 检查是否达到指定次数
        if args.count > 0 and count >= args.count:
            print(f"\n✅ 完成 {args.count} 次上报")
            break
        
        # 等待下次上报
        if args.interval > 0:
            print(f"⏳ 等待 {args.interval} 秒...")
            time.sleep(args.interval)

if __name__ == '__main__':
    main() 