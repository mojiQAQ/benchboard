#!/usr/bin/env python3

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import json
import urllib.parse
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 简单的内存存储
teams_data = {}

@app.route('/')
def dashboard():
    """简单的Web看板"""
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>BenchBoard - 性能监控</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .header { text-align: center; margin-bottom: 30px; }
            .teams { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
            .team-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .team-name { font-size: 1.2em; font-weight: bold; margin-bottom: 15px; color: #333; }
            .metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
            .metric { padding: 10px; background: #f8f9fa; border-radius: 5px; text-align: center; }
            .metric-value { font-size: 1.1em; font-weight: bold; }
            .metric-label { font-size: 0.8em; color: #666; }
            .qps { background: #d4edda; color: #155724; }
            .latency { background: #d1ecf1; color: #0c5460; }
            .p99 { background: #fff3cd; color: #856404; }
            .loss { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚀 BenchBoard 性能监控看板</h1>
            <p>实时监控各小组QPS、延迟、数据丢失率等关键指标</p>
        </div>
        <div class="teams" id="teams">
            <div class="team-card">
                <div class="team-name">等待数据...</div>
                <div>暂无团队数据</div>
            </div>
        </div>
        
        <script>
            function updateDashboard() {
                fetch('/api/teams')
                    .then(response => response.json())
                    .then(data => {
                        const container = document.getElementById('teams');
                        if (data.length === 0) {
                            container.innerHTML = '<div class="team-card"><div class="team-name">等待数据...</div><div>暂无团队数据</div></div>';
                            return;
                        }
                        
                        container.innerHTML = '';
                        data.forEach(team => {
                            const card = document.createElement('div');
                            card.className = 'team-card';
                            card.innerHTML = `
                                <div class="team-name">${team.team_name}</div>
                                <div class="metrics">
                                    <div class="metric qps">
                                        <div class="metric-value">${team.qps || '0'}</div>
                                        <div class="metric-label">QPS</div>
                                    </div>
                                    <div class="metric latency">
                                        <div class="metric-value">${team.avg_latency || '0'}ms</div>
                                        <div class="metric-label">平均延迟</div>
                                    </div>
                                    <div class="metric p99">
                                        <div class="metric-value">${team.p99_latency || '0'}ms</div>
                                        <div class="metric-label">P99延迟</div>
                                    </div>
                                    <div class="metric loss">
                                        <div class="metric-value">${team.data_loss_rate || '0'}%</div>
                                        <div class="metric-label">数据丢失率</div>
                                    </div>
                                </div>
                                <div style="margin-top: 10px; font-size: 0.8em; color: #666;">
                                    最后更新: ${new Date(team.last_update).toLocaleTimeString()}
                                </div>
                            `;
                            container.appendChild(card);
                        });
                    })
                    .catch(error => console.error('Error:', error));
            }
            
            // 每3秒更新一次
            setInterval(updateDashboard, 3000);
            updateDashboard();
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/api/stats/report', methods=['POST'])
def submit_stats():
    """接收压测结果上报"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        team_id = request.headers.get('X-Team-ID')
        encoded_team_name = request.headers.get('X-Team-Name', f'Team-{team_id}')
        
        try:
            team_name = urllib.parse.unquote(encoded_team_name)
        except:
            team_name = encoded_team_name
        
        if not team_id:
            return jsonify({"error": "X-Team-ID header is required"}), 400
        
        # 计算关键指标
        qps = data.get('performanceMetrics', {}).get('avgCompletedQPS', 0)
        
        # 计算平均延迟
        latency_analysis = data.get('latencyAnalysis', {})
        total_latency = 0
        total_requests = 0
        
        for op_type in ['sensorData', 'sensorRW', 'batchRW', 'query']:
            if op_type in latency_analysis:
                op_data = latency_analysis[op_type]
                op_requests = sum(op_data.get('buckets', []))
                if op_requests > 0:
                    total_latency += op_data.get('avg', 0) * op_requests
                    total_requests += op_requests
        
        avg_latency = total_latency / total_requests if total_requests > 0 else 0
        
        # 计算P99延迟
        sensor_buckets = latency_analysis.get('sensorData', {}).get('buckets', [])
        p99_latency = calculate_p99(sensor_buckets)
        
        # 计算数据丢失率
        total_sent = data.get('totalSent', 0)
        total_ops = data.get('totalOps', 0)
        pending = data.get('pending', 0)
        data_loss_rate = 0
        if total_sent > 0:
            lost = total_sent - total_ops - pending
            data_loss_rate = (lost / total_sent) * 100 if lost > 0 else 0
        
        # 保存数据
        teams_data[team_id] = {
            'team_id': team_id,
            'team_name': team_name,
            'last_update': datetime.now().isoformat(),
            'qps': round(qps, 1),
            'avg_latency': round(avg_latency, 1),
            'p99_latency': round(p99_latency, 1),
            'data_loss_rate': round(data_loss_rate, 2),
            'stats': data
        }
        
        return jsonify({"message": "Stats submitted successfully", "team_id": team_id}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

def calculate_p99(buckets):
    """简单的P99计算"""
    if not buckets or sum(buckets) == 0:
        return 0
    
    bucket_boundaries = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, float('inf')]
    total_requests = sum(buckets)
    p99_threshold = total_requests * 0.99
    cumulative = 0
    
    for i, count in enumerate(buckets):
        cumulative += count
        if cumulative >= p99_threshold:
            return bucket_boundaries[i] if i < len(bucket_boundaries) else 5000
    
    return 5000

@app.route('/api/teams', methods=['GET'])
def get_teams():
    """获取所有团队数据"""
    return jsonify(list(teams_data.values()))

if __name__ == '__main__':
    print("🚀 Starting Simple BenchBoard server on port 8082...")
    app.run(host='0.0.0.0', port=8082, debug=True) 