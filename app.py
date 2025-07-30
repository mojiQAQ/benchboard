import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from pydantic import BaseModel, Field
from dataclasses import dataclass
import threading
import time
import urllib.parse

app = Flask(__name__)
app.config['SECRET_KEY'] = 'benchboard-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# 数据存储
@dataclass
class TeamData:
    team_id: str
    team_name: str
    last_update: datetime
    stats: Dict
    is_active: bool = True
    best_qps: float = 0.0
    best_qps_time: Optional[datetime] = None
    best_latency: float = float('inf')
    best_latency_time: Optional[datetime] = None

# 全局存储
teams_data: Dict[str, TeamData] = {}
data_lock = threading.Lock()

# Pydantic模型定义
class OperationStat(BaseModel):
    operations: int = Field(..., description="操作数量")
    errors: int = Field(..., description="错误数量")

class OperationsStats(BaseModel):
    sensorData: OperationStat
    sensorRW: OperationStat
    batchRW: OperationStat
    query: OperationStat

class HighPriorityStats(BaseModel):
    sensorDataCount: int = Field(..., description="传感器数据上报高优先级请求数")
    sensorRWCount: int = Field(..., description="传感器读写操作高优先级请求数")
    batchRWCount: int = Field(..., description="批量操作高优先级请求数")
    queryCount: int = Field(..., description="查询操作高优先级请求数")
    totalCount: int = Field(..., description="高优先级请求总数")
    percentage: float = Field(..., description="高优先级请求占比（%）")

class PerformanceMetrics(BaseModel):
    avgSentQPS: float = Field(..., description="平均发送 QPS")
    avgCompletedQPS: float = Field(..., description="平均完成 QPS")
    errorRate: float = Field(..., description="错误率（%）")

class LatencyDistribution(BaseModel):
    avg: float = Field(..., description="平均延迟（ms）")
    min: float = Field(..., description="最小延迟（ms）")
    max: float = Field(..., description="最大延迟（ms）")
    buckets: List[int] = Field(..., description="延迟分布桶计数")
    highPriorityCount: Optional[int] = Field(None, description="高优先级请求数量")
    highPriorityAvg: Optional[float] = Field(None, description="高优先级平均延迟（ms）")
    highPriorityMin: Optional[float] = Field(None, description="高优先级最小延迟（ms）")
    highPriorityMax: Optional[float] = Field(None, description="高优先级最大延迟（ms）")
    highPriorityBuckets: Optional[List[int]] = Field(None, description="高优先级延迟分布桶计数")

class LatencyAnalysis(BaseModel):
    sensorData: LatencyDistribution
    sensorRW: LatencyDistribution
    batchRW: LatencyDistribution
    query: LatencyDistribution

class StatsReport(BaseModel):
    totalElapsed: float = Field(..., description="总运行时间（秒）")
    totalSent: int = Field(..., description="发送请求数")
    totalOps: int = Field(..., description="完成请求数")
    totalErrors: int = Field(..., description="总错误数")
    totalSaveDelayErrors: int = Field(..., description="总因为发现落盘时间超时而产生的错误数")
    pending: int = Field(..., description="待处理请求数")
    operations: OperationsStats
    highPriorityStats: HighPriorityStats
    performanceMetrics: PerformanceMetrics
    latencyAnalysis: LatencyAnalysis

def calculate_p99_latency(buckets: List[int]) -> float:
    """计算P99延迟"""
    bucket_boundaries = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, float('inf')]
    total_requests = sum(buckets)
    if total_requests == 0:
        return 0.0
    
    p99_threshold = total_requests * 0.99
    cumulative = 0
    
    for i, count in enumerate(buckets):
        cumulative += count
        if cumulative >= p99_threshold:
            if i == 0:
                return bucket_boundaries[i]
            else:
                # 线性插值
                prev_cumulative = cumulative - count
                ratio = (p99_threshold - prev_cumulative) / count
                lower_bound = bucket_boundaries[i-1] if i > 0 else 0
                upper_bound = bucket_boundaries[i]
                return lower_bound + ratio * (upper_bound - lower_bound)
    
    return bucket_boundaries[-2]  # 返回最后一个有限边界

def calculate_data_loss_rate(stats: Dict) -> float:
    """计算数据丢失率"""
    total_sent = stats.get('totalSent', 0)
    total_ops = stats.get('totalOps', 0)
    pending = stats.get('pending', 0)
    
    if total_sent == 0:
        return 0.0
    
    # 数据丢失 = 发送数 - 完成数 - 待处理数
    lost = total_sent - total_ops - pending
    return (lost / total_sent) * 100 if lost > 0 else 0.0

def calculate_overall_metrics(stats: Dict) -> Dict:
    """计算整体性能指标"""
    latency_analysis = stats.get('latencyAnalysis', {})
    
    # 计算总体平均延迟
    total_latency = 0
    total_requests = 0
    
    for operation_type in ['sensorData', 'sensorRW', 'batchRW', 'query']:
        if operation_type in latency_analysis:
            op_data = latency_analysis[operation_type]
            op_requests = sum(op_data.get('buckets', []))
            if op_requests > 0:
                total_latency += op_data.get('avg', 0) * op_requests
                total_requests += op_requests
    
    avg_latency = total_latency / total_requests if total_requests > 0 else 0
    
    # 计算总体P99延迟（使用sensorData作为主要指标）
    sensor_buckets = latency_analysis.get('sensorData', {}).get('buckets', [])
    p99_latency = calculate_p99_latency(sensor_buckets)
    
    # 计算高优先级平均延迟
    high_priority_latency = 0
    high_priority_count = 0
    
    for operation_type in ['sensorData', 'sensorRW', 'batchRW', 'query']:
        if operation_type in latency_analysis:
            op_data = latency_analysis[operation_type]
            if op_data.get('highPriorityAvg') and op_data.get('highPriorityCount'):
                high_priority_latency += op_data['highPriorityAvg'] * op_data['highPriorityCount']
                high_priority_count += op_data['highPriorityCount']
    
    avg_high_priority_latency = high_priority_latency / high_priority_count if high_priority_count > 0 else 0
    
    return {
        'avg_latency': avg_latency,
        'p99_latency': p99_latency,
        'high_priority_latency': avg_high_priority_latency,
        'data_loss_rate': calculate_data_loss_rate(stats)
    }

def save_team_data(team_id: str, team_name: str, stats: Dict):
    """保存团队数据到本地文件"""
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    filename = f"{data_dir}/{team_id}.json"
    data = {
        "team_id": team_id,
        "team_name": team_name,
        "timestamp": datetime.now().isoformat(),
        "stats": stats
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_team_data(team_id: str) -> Optional[Dict]:
    """从本地文件加载团队数据"""
    filename = f"data/{team_id}.json"
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

@app.route('/')
def dashboard():
    """Web看板页面"""
    return render_template('dashboard.html')

@app.route('/api/stats/report', methods=['POST'])
def submit_stats():
    """接收压测结果上报"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # 验证数据格式
        stats_report = StatsReport(**data)
        
        # 获取团队信息
        team_id = request.headers.get('X-Team-ID')
        encoded_team_name = request.headers.get('X-Team-Name', f'Team-{team_id}')
        
        # 解码URL编码的团队名称
        try:
            team_name = urllib.parse.unquote(encoded_team_name)
        except:
            team_name = encoded_team_name  # 如果解码失败，使用原始值
        
        if not team_id:
            return jsonify({"error": "X-Team-ID header is required"}), 400
        
        # 计算性能指标
        current_qps = data.get('performanceMetrics', {}).get('avgCompletedQPS', 0)
        current_metrics = calculate_overall_metrics(data)
        current_latency = current_metrics['avg_latency']
        
        # 保存数据
        with data_lock:
            if team_id in teams_data:
                team_data = teams_data[team_id]
                # 更新最佳QPS记录
                if current_qps > team_data.best_qps:
                    team_data.best_qps = current_qps
                    team_data.best_qps_time = datetime.now()
                
                # 更新最佳延迟记录
                if current_latency > 0 and current_latency < team_data.best_latency:
                    team_data.best_latency = current_latency
                    team_data.best_latency_time = datetime.now()
                
                # 更新其他信息
                team_data.team_name = team_name
                team_data.last_update = datetime.now()
                team_data.stats = data
                team_data.is_active = True
            else:
                teams_data[team_id] = TeamData(
                    team_id=team_id,
                    team_name=team_name,
                    last_update=datetime.now(),
                    stats=data,
                    best_qps=current_qps,
                    best_qps_time=datetime.now() if current_qps > 0 else None,
                    best_latency=current_latency if current_latency > 0 else float('inf'),
                    best_latency_time=datetime.now() if current_latency > 0 else None
                )
        
        # 保存到本地文件
        save_team_data(team_id, team_name, data)
        
        # 通过WebSocket广播更新
        socketio.emit('stats_update', {
            'team_id': team_id,
            'team_name': team_name,
            'stats': data,
            'timestamp': datetime.now().isoformat(),
            'metrics': current_metrics,
            'best_qps': teams_data[team_id].best_qps,
            'best_qps_time': teams_data[team_id].best_qps_time.isoformat() if teams_data[team_id].best_qps_time else None,
            'best_latency': teams_data[team_id].best_latency if teams_data[team_id].best_latency != float('inf') else None,
            'best_latency_time': teams_data[team_id].best_latency_time.isoformat() if teams_data[team_id].best_latency_time else None
        })
        
        return jsonify({"message": "Stats submitted successfully", "team_id": team_id}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/teams', methods=['GET'])
def get_teams():
    """获取所有团队数据"""
    with data_lock:
        teams_list = []
        for team_id, team_data in teams_data.items():
            teams_list.append({
                'team_id': team_id,
                'team_name': team_data.team_name,
                'last_update': team_data.last_update.isoformat(),
                'is_active': team_data.is_active
            })
        return jsonify(teams_list)

@app.route('/api/teams/<team_id>', methods=['GET'])
def get_team_stats(team_id):
    """获取特定团队的统计数据"""
    with data_lock:
        if team_id in teams_data:
            team_data = teams_data[team_id]
            metrics = calculate_overall_metrics(team_data.stats)
            return jsonify({
                'team_id': team_id,
                'team_name': team_data.team_name,
                'last_update': team_data.last_update.isoformat(),
                'stats': team_data.stats,
                'metrics': metrics,
                'best_qps': team_data.best_qps,
                'best_qps_time': team_data.best_qps_time.isoformat() if team_data.best_qps_time else None,
                'best_latency': team_data.best_latency if team_data.best_latency != float('inf') else None,
                'best_latency_time': team_data.best_latency_time.isoformat() if team_data.best_latency_time else None
            })
        else:
            return jsonify({"error": "Team not found"}), 404

@app.route('/api/teams/<team_id>/history', methods=['GET'])
def get_team_history(team_id):
    """获取团队历史数据"""
    data = load_team_data(team_id)
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "Team history not found"}), 404

@socketio.on('connect')
def handle_connect():
    """客户端连接时发送当前数据"""
    with data_lock:
        for team_id, team_data in teams_data.items():
            metrics = calculate_overall_metrics(team_data.stats)
            emit('stats_update', {
                'team_id': team_id,
                'team_name': team_data.team_name,
                'stats': team_data.stats,
                'timestamp': team_data.last_update.isoformat(),
                'metrics': metrics,
                'best_qps': team_data.best_qps,
                'best_qps_time': team_data.best_qps_time.isoformat() if team_data.best_qps_time else None,
                'best_latency': team_data.best_latency if team_data.best_latency != float('inf') else None,
                'best_latency_time': team_data.best_latency_time.isoformat() if team_data.best_latency_time else None
            })

def cleanup_inactive_teams():
    """清理不活跃的团队（超过5分钟没有更新）"""
    while True:
        time.sleep(60)  # 每分钟检查一次
        current_time = datetime.now()
        with data_lock:
            inactive_teams = []
            for team_id, team_data in teams_data.items():
                if (current_time - team_data.last_update).total_seconds() > 300:  # 5分钟
                    team_data.is_active = False
                    inactive_teams.append(team_id)
            
            # 移除不活跃的团队
            for team_id in inactive_teams:
                del teams_data[team_id]

if __name__ == '__main__':
    # 启动清理线程
    cleanup_thread = threading.Thread(target=cleanup_inactive_teams, daemon=True)
    cleanup_thread.start()
    
    print("🚀 Starting BenchBoard server on port 8080...")
    
    # 启动服务器
    socketio.run(app, host='0.0.0.0', port=8080, debug=True) 