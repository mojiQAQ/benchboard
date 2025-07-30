#!/usr/bin/env python3
"""
API测试脚本 - 验证BenchBoard服务器功能
"""

import requests
import json
import time
import urllib.parse

# 使用示例数据
with open('example_data.json', 'r', encoding='utf-8') as f:
    example_data = json.load(f)

def test_server_health():
    """测试服务器健康状态"""
    try:
        response = requests.get('http://localhost:8080/api/teams', timeout=5)
        if response.status_code == 200:
            print("✅ 服务器运行正常")
            return True
        else:
            print(f"❌ 服务器响应异常: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到服务器: {e}")
        return False

def test_stats_submission():
    """测试统计数据提交"""
    team_name = "测试小组1"
    encoded_team_name = urllib.parse.quote(team_name, safe='')
    
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Accept-Charset': 'utf-8',
        'X-Team-ID': 'test-team-1',
        'X-Team-Name': encoded_team_name
    }
    
    try:
        response = requests.post(
            'http://localhost:8080/api/stats/report',
            headers=headers,
            data=json.dumps(example_data, ensure_ascii=False).encode('utf-8'),
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 数据提交成功: {result}")
            return True
        else:
            print(f"❌ 数据提交失败: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 提交请求失败: {e}")
        return False

def test_team_data_retrieval():
    """测试团队数据获取"""
    try:
        # 获取团队列表
        response = requests.get('http://localhost:8080/api/teams', timeout=5)
        if response.status_code == 200:
            teams = response.json()
            print(f"✅ 获取团队列表成功: {len(teams)} 个团队")
            
            # 获取特定团队数据
            if teams:
                team_id = teams[0]['team_id']
                response = requests.get(f'http://localhost:8080/api/teams/{team_id}', timeout=5)
                if response.status_code == 200:
                    team_data = response.json()
                    print(f"✅ 获取团队数据成功: {team_data['team_name']}")
                    return True
                else:
                    print(f"❌ 获取团队数据失败: {response.status_code}")
                    return False
            else:
                print("⚠️  没有找到团队数据")
                return True
        else:
            print(f"❌ 获取团队列表失败: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 获取数据失败: {e}")
        return False

def test_web_dashboard():
    """测试Web看板访问"""
    try:
        response = requests.get('http://localhost:8080/', timeout=5)
        if response.status_code == 200:
            print("✅ Web看板访问正常")
            return True
        else:
            print(f"❌ Web看板访问失败: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Web看板访问失败: {e}")
        return False

def main():
    print("🧪 开始API测试")
    print("=" * 50)
    
    # 等待服务器启动
    print("⏳ 等待服务器启动...")
    time.sleep(2)
    
    # 测试服务器健康状态
    print("\n1. 测试服务器健康状态")
    if not test_server_health():
        print("❌ 服务器未启动，请先运行: python app.py")
        return
    
    # 测试Web看板
    print("\n2. 测试Web看板")
    test_web_dashboard()
    
    # 测试数据提交
    print("\n3. 测试数据提交")
    if test_stats_submission():
        # 等待数据保存
        time.sleep(1)
        
        # 测试数据获取
        print("\n4. 测试数据获取")
        test_team_data_retrieval()
    
    print("\n" + "=" * 50)
    print("🎉 API测试完成")
    print("📊 访问 http://localhost:8080 查看Web看板")

if __name__ == '__main__':
    main() 