#!/usr/bin/env python3

import requests
import json
import urllib.parse
import time
import threading

def start_server():
    """启动服务器"""
    import simple_app
    simple_app.app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

def test_api():
    """测试API功能"""
    time.sleep(2)  # 等待服务器启动
    
    # 准备测试数据
    test_data = {
        "totalElapsed": 120.5,
        "totalSent": 5000,
        "totalOps": 4850,
        "totalErrors": 150,
        "totalSaveDelayErrors": 45,
        "pending": 25,
        "operations": {
            "sensorData": {"operations": 2000, "errors": 60},
            "sensorRW": {"operations": 1500, "errors": 45},
            "batchRW": {"operations": 800, "errors": 25},
            "query": {"operations": 550, "errors": 20}
        },
        "highPriorityStats": {
            "sensorDataCount": 300,
            "sensorRWCount": 200,
            "batchRWCount": 100,
            "queryCount": 50,
            "totalCount": 650,
            "percentage": 13.0
        },
        "performanceMetrics": {
            "avgSentQPS": 41.5,
            "avgCompletedQPS": 40.2,
            "errorRate": 3.09
        },
        "latencyAnalysis": {
            "sensorData": {
                "avg": 45.2,
                "min": 12.5,
                "max": 1250.8,
                "buckets": [150, 200, 180, 160, 140, 120, 100, 80, 60, 40, 20, 10, 5]
            },
            "sensorRW": {
                "avg": 78.5,
                "min": 25.3,
                "max": 2100.2,
                "buckets": [120, 150, 130, 110, 90, 70, 50, 40, 30, 20, 15, 10, 5]
            },
            "batchRW": {
                "avg": 125.8,
                "min": 45.6,
                "max": 3500.5,
                "buckets": [80, 100, 90, 70, 60, 50, 40, 30, 25, 20, 15, 10, 5]
            },
            "query": {
                "avg": 95.3,
                "min": 35.2,
                "max": 2800.1,
                "buckets": [100, 120, 110, 90, 75, 60, 45, 35, 25, 20, 15, 10, 5]
            }
        }
    }
    
    # 测试多个团队
    teams = [
        ("team1", "第一小组"),
        ("team2", "第二小组"),
        ("team3", "第三小组")
    ]
    
    for team_id, team_name in teams:
        try:
            encoded_name = urllib.parse.quote(team_name, safe='')
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'X-Team-ID': team_id,
                'X-Team-Name': encoded_name
            }
            
            # 为每个团队生成略微不同的数据
            team_data = test_data.copy()
            team_data['performanceMetrics']['avgCompletedQPS'] *= (0.8 + 0.4 * hash(team_id) % 100 / 100)
            
            response = requests.post(
                'http://localhost:8080/api/stats/report',
                headers=headers,
                data=json.dumps(team_data, ensure_ascii=False).encode('utf-8'),
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"✅ {team_name} 数据提交成功")
            else:
                print(f"❌ {team_name} 数据提交失败: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {team_name} 提交出错: {e}")
            
        time.sleep(1)
    
    # 检查API结果
    try:
        response = requests.get('http://localhost:8080/api/teams', timeout=5)
        if response.status_code == 200:
            teams_data = response.json()
            print(f"\n📊 当前有 {len(teams_data)} 个团队:")
            for team in teams_data:
                print(f"   {team['team_name']}: QPS={team['qps']}, 延迟={team['avg_latency']}ms, P99={team['p99_latency']}ms")
        else:
            print(f"❌ 获取团队数据失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 获取团队数据出错: {e}")
    
    print(f"\n🌐 访问 http://localhost:8080 查看看板")

if __name__ == '__main__':
    print("🚀 启动BenchBoard演示...")
    
    # 在后台启动服务器
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # 运行API测试
    test_api()
    
    print("\n按 Ctrl+C 退出...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 演示结束") 