import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from pydantic import BaseModel, Field
from dataclasses import dataclass
import threading
import time
import urllib.parse
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'benchboard-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# 缓存结构
@dataclass 
class TeamCache:
    file_count: int = 0
    last_scan_time: Optional[datetime] = None
    best_records_cached: bool = False
    file_mtime_hash: str = ""

# 全局存储
teams_data: Dict[str, TeamData] = {}
team_cache: Dict[str, TeamCache] = {}
data_lock = threading.Lock()
cache_lock = threading.Lock()

# 性能配置
CACHE_EXPIRE_SECONDS = 300  # 缓存5分钟过期
MAX_WORKER_THREADS = 4      # 最大并发线程数
BATCH_SIZE = 50             # 批量处理文件数量

# Pydantic模型定义
class OperationStat(BaseModel):
    operations: int = Field(..., description="操作数量")
    errors: int = Field(..., description="错误数量")

class OperationsStats(BaseModel):
    sensorData: OperationStat

class HighPriorityStats(BaseModel):
    sensorDataCount: int = Field(..., description="传感器数据上报高优先级请求数")
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

class StatsReport(BaseModel):
    totalElapsed: float = Field(..., description="总运行时间（秒）")
    totalSent: int = Field(..., description="发送请求数")
    totalOps: int = Field(..., description="完成请求数")
    totalErrors: int = Field(..., description="总错误数")
    totalSaveDelayErrors: int = Field(..., description="总因为发现落盘时间超时而产生的错误数")
    totalAvgLatency: Optional[float] = Field(None, description="总平均延迟（ms）")
    highPriorityAvgDelayLatency: Optional[float] = Field(None, description="高优先级平均延迟（ms）")
    totalVerifyErrorRate: Optional[float] = Field(None, description="总验证错误率（%）")
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
    """计算失败率"""
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
    # 优先使用新的字段
    avg_latency = stats.get('totalAvgLatency')
    high_priority_latency = stats.get('highPriorityAvgDelayLatency')
    
    # 如果新字段不存在，回退到旧的计算方式
    if avg_latency is None:
        latency_analysis = stats.get('latencyAnalysis', {})
        
        # 现在只处理sensorData操作类型
        if 'sensorData' in latency_analysis:
            op_data = latency_analysis['sensorData']
            op_requests = sum(op_data.get('buckets', []))
            if op_requests > 0:
                avg_latency = op_data.get('avg', 0)
            else:
                avg_latency = 0
        else:
            avg_latency = 0
    
    # 如果高优先级延迟字段不存在，回退到旧的计算方式
    if high_priority_latency is None:
        latency_analysis = stats.get('latencyAnalysis', {})
        
        # 现在只处理sensorData操作类型
        if 'sensorData' in latency_analysis:
            op_data = latency_analysis['sensorData']
            if op_data.get('highPriorityAvg') and op_data.get('highPriorityCount'):
                high_priority_latency = op_data['highPriorityAvg']
            else:
                high_priority_latency = 0
        else:
            high_priority_latency = 0
    
    # 计算总体P99延迟（使用sensorData作为主要指标）
    latency_analysis = stats.get('latencyAnalysis', {})
    sensor_buckets = latency_analysis.get('sensorData', {}).get('buckets', [])
    p99_latency = calculate_p99_latency(sensor_buckets)
    
    return {
        'avg_latency': avg_latency,
        'p99_latency': p99_latency,
        'high_priority_latency': high_priority_latency,
        'data_loss_rate': calculate_data_loss_rate(stats)
    }

def save_team_data(team_id: str, team_name: str, stats: Dict):
    """保存团队数据到本地文件 - 每次上报都单独存储"""
    # 创建团队目录
    team_dir = f"data/{team_id}"
    if not os.path.exists(team_dir):
        os.makedirs(team_dir)
    
    # 使用时间戳作为文件名
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 精确到毫秒
    filename = f"{team_dir}/{timestamp_str}.json"
    
    data = {
        "team_id": team_id,
        "team_name": team_name,
        "timestamp": timestamp.isoformat(),
        "stats": stats
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 同时保存最新数据到 latest.json 以便快速访问
    latest_filename = f"{team_dir}/latest.json"
    with open(latest_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_team_data(team_id: str) -> Optional[Dict]:
    """从本地文件加载团队最新数据"""
    filename = f"data/{team_id}/latest.json"
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def get_file_mtime_hash(team_dir: str) -> str:
    """获取团队目录文件修改时间的哈希值，用于缓存失效检测"""
    try:
        json_files = glob.glob(f"{team_dir}/*.json")
        if not json_files:
            return ""
        
        mtime_list = []
        for file_path in json_files:
            try:
                mtime = os.path.getmtime(file_path)
                mtime_list.append(f"{os.path.basename(file_path)}:{mtime}")
            except OSError:
                continue
        
        # 创建简单的哈希
        content = "|".join(sorted(mtime_list))
        return str(hash(content))
    except Exception:
        return ""

def get_team_history_files_cached(team_id: str) -> List[Dict]:
    """获取团队所有历史数据文件列表（带缓存优化）"""
    team_dir = f"data/{team_id}"
    if not os.path.exists(team_dir):
        return []
    
    with cache_lock:
        # 检查缓存是否有效
        cache_entry = team_cache.get(team_id)
        current_mtime_hash = get_file_mtime_hash(team_dir)
        
        if (cache_entry and 
            cache_entry.file_mtime_hash == current_mtime_hash and
            cache_entry.last_scan_time and
            (datetime.now() - cache_entry.last_scan_time).total_seconds() < CACHE_EXPIRE_SECONDS):
            # 缓存有效，从缓存读取
            logger.debug(f"使用缓存的文件列表: {team_id}")
    
    # 缓存无效或不存在，重新扫描
    history_files = []
    json_files = glob.glob(f"{team_dir}/*.json")
    
    # 使用文件名进行时间戳解析（避免读取文件内容）
    for file_path in json_files:
        filename = os.path.basename(file_path)
        if filename == 'latest.json':
            continue
            
        # 尝试从文件名解析时间戳
        try:
            # 假设文件名格式为: 20250801_171514_920.json
            name_part = filename.replace('.json', '')
            if '_' in name_part and len(name_part) >= 17:
                timestamp_str = f"{name_part[:8]}T{name_part[9:11]}:{name_part[11:13]}:{name_part[13:15]}.{name_part[16:]}"
                timestamp = timestamp_str.replace('_', 'T').replace('T', '-', 2).replace('-', 'T', 1)
                history_files.append({
                    'filename': filename,
                    'timestamp': timestamp,
                    'file_path': file_path
                })
            else:
                # 回退到读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    history_files.append({
                        'filename': filename,
                        'timestamp': data.get('timestamp'),
                        'file_path': file_path
                    })
        except Exception as e:
            logger.warning(f"⚠️ 读取文件失败 {file_path}: {e}")
            continue
    
    # 按时间戳排序（最新的在前）
    history_files.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # 更新缓存
    with cache_lock:
        team_cache[team_id] = TeamCache(
            file_count=len(history_files),
            last_scan_time=datetime.now(),
            file_mtime_hash=current_mtime_hash
        )
    
    return history_files

def get_team_history_files(team_id: str) -> List[Dict]:
    """获取团队所有历史数据文件列表（兼容性包装）"""
    return get_team_history_files_cached(team_id)

def load_team_history_data(team_id: str, limit: int = 10) -> List[Dict]:
    """加载团队历史数据（限制数量）"""
    history_files = get_team_history_files(team_id)
    history_data = []
    
    for file_info in history_files[:limit]:
        try:
            with open(file_info['file_path'], 'r', encoding='utf-8') as f:
                data = json.load(f)
                history_data.append(data)
        except Exception as e:
            print(f"Error loading {file_info['file_path']}: {e}")
            continue
    
    return history_data

def load_single_team(team_dir_name: str) -> Optional[TeamData]:
    """加载单个团队数据（用于并发加载）"""
    try:
        team_dir_path = os.path.join("data", team_dir_name)
        
        # 跳过非目录文件
        if not os.path.isdir(team_dir_path):
            return None
            
        latest_file = os.path.join(team_dir_path, "latest.json")
        
        # 如果latest.json存在，加载团队数据
        if not os.path.exists(latest_file):
            return None
            
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        team_id = data.get('team_id', team_dir_name)
        team_name = data.get('team_name', f'Team-{team_id}')
        timestamp_str = data.get('timestamp')
        stats = data.get('stats', {})
        
        # 解析时间戳
        try:
            last_update = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now()
        except:
            last_update = datetime.now()
        
        # 计算最佳记录
        best_qps, best_qps_time, best_latency, best_latency_time = calculate_best_records(team_id)
        
        # 创建TeamData对象
        team_data = TeamData(
            team_id=team_id,
            team_name=team_name,
            last_update=last_update,
            stats=stats,
            is_active=True,  # 启动时都设为活跃
            best_qps=best_qps,
            best_qps_time=best_qps_time,
            best_latency=best_latency,
            best_latency_time=best_latency_time
        )
        
        logger.info(f"✅ 加载团队: {team_name} (ID: {team_id})")
        logger.info(f"   最后更新: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        if best_latency is not None:
            logger.info(f"   最佳QPS: {best_qps:.1f} | 最佳延迟: {best_latency:.1f}ms")
        else:
            logger.info(f"   最佳QPS: {best_qps:.1f} | 最佳延迟: N/A")
        
        return team_data
        
    except Exception as e:
        logger.error(f"❌ 加载团队 {team_dir_name} 失败: {e}")
        return None

def load_all_teams_on_startup():
    """启动时从data目录读取所有团队数据 - 优化版本（支持并发加载）"""
    logger.info("🔄 启动时加载历史数据...")
    
    data_dir = "data"
    if not os.path.exists(data_dir):
        logger.warning("📁 data目录不存在，跳过数据加载")
        return 0
    
    # 获取所有团队目录
    team_dirs = []
    try:
        for item in os.listdir(data_dir):
            team_dir_path = os.path.join(data_dir, item)
            if os.path.isdir(team_dir_path):
                team_dirs.append(item)
    except Exception as e:
        logger.error(f"扫描data目录失败: {e}")
        return 0
    
    if not team_dirs:
        logger.info("📁 data目录下没有找到团队数据")
        return 0
    
    loaded_teams = 0
    failed_teams = []
    
    # 使用并发加载团队数据
    logger.info(f"🔄 发现 {len(team_dirs)} 个团队目录，开始并发加载...")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKER_THREADS) as executor:
        # 提交所有加载任务
        future_to_team = {executor.submit(load_single_team, team_dir): team_dir for team_dir in team_dirs}
        
        # 收集结果
        for future in as_completed(future_to_team):
            team_dir = future_to_team[future]
            try:
                team_data = future.result()
                if team_data:
                    with data_lock:
                        teams_data[team_data.team_id] = team_data
                    loaded_teams += 1
                else:
                    failed_teams.append(team_dir)
            except Exception as e:
                logger.error(f"处理团队 {team_dir} 的结果时失败: {e}")
                failed_teams.append(team_dir)
    
    # 输出加载结果
    logger.info(f"📊 共加载 {loaded_teams} 个团队的历史数据")
    if failed_teams:
        logger.warning(f"⚠️ 加载失败的团队: {', '.join(failed_teams)}")
    
    # 清理缓存状态
    with cache_lock:
        for team_id in teams_data.keys():
            if team_id not in team_cache:
                team_cache[team_id] = TeamCache()
    
    return loaded_teams

def get_cache_status() -> Dict:
    """获取缓存状态信息（用于调试和监控）"""
    with cache_lock:
        cache_info = {}
        for team_id, cache_entry in team_cache.items():
            cache_info[team_id] = {
                'file_count': cache_entry.file_count,
                'last_scan_time': cache_entry.last_scan_time.isoformat() if cache_entry.last_scan_time else None,
                'best_records_cached': cache_entry.best_records_cached,
                'cache_age_seconds': (datetime.now() - cache_entry.last_scan_time).total_seconds() if cache_entry.last_scan_time else None
            }
        return cache_info

def clear_team_cache(team_id: str = None):
    """清理团队缓存"""
    with cache_lock:
        if team_id:
            if team_id in team_cache:
                del team_cache[team_id]
                logger.info(f"已清理团队 {team_id} 的缓存")
        else:
            team_cache.clear()
            logger.info("已清理所有团队缓存")

def calculate_best_records_batch(file_paths: List[str]) -> Tuple[float, datetime, float, datetime]:
    """批量计算最佳记录（用于并发处理）"""
    best_qps = 0.0
    best_qps_time = None
    best_latency = float('inf')
    best_latency_time = None
    
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            stats = data.get('stats', {})
            timestamp_str = data.get('timestamp')
            
            # 解析时间戳
            try:
                timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else None
            except:
                timestamp = None
            
            # 获取QPS
            current_qps = stats.get('performanceMetrics', {}).get('avgCompletedQPS', 0)
            if current_qps > best_qps:
                best_qps = current_qps
                best_qps_time = timestamp
            
            # 计算当前延迟
            current_metrics = calculate_overall_metrics(stats)
            current_latency = current_metrics.get('avg_latency', 0)
            
            # 更新最佳延迟（更小的更好）
            if current_latency > 0 and current_latency < best_latency:
                best_latency = current_latency
                best_latency_time = timestamp
                
        except Exception as e:
            logger.warning(f"⚠️ 读取历史文件失败 {file_path}: {e}")
            continue
    
    return best_qps, best_qps_time, best_latency, best_latency_time

def calculate_best_records(team_id: str) -> Tuple[float, datetime, float, datetime]:
    """计算团队的最佳记录（QPS和延迟）- 优化版本"""
    
    # 检查缓存
    with cache_lock:
        cache_entry = team_cache.get(team_id)
        if (cache_entry and cache_entry.best_records_cached and
            cache_entry.last_scan_time and
            (datetime.now() - cache_entry.last_scan_time).total_seconds() < CACHE_EXPIRE_SECONDS):
            logger.debug(f"使用缓存的最佳记录: {team_id}")
            # 这里应该返回缓存的值，但为了简化，我们重新计算
    
    best_qps = 0.0
    best_qps_time = None
    best_latency = float('inf')
    best_latency_time = None
    
    try:
        # 获取所有历史文件
        history_files = get_team_history_files(team_id)
        
        if not history_files:
            return best_qps, best_qps_time, None, None
        
        file_paths = [f['file_path'] for f in history_files]
        
        # 如果文件数量较少，直接处理
        if len(file_paths) <= BATCH_SIZE:
            best_qps, best_qps_time, best_latency, best_latency_time = calculate_best_records_batch(file_paths)
        else:
            # 文件数量较多，使用并发处理
            logger.info(f"团队 {team_id} 有 {len(file_paths)} 个文件，使用并发处理")
            
            # 分批处理
            batches = [file_paths[i:i + BATCH_SIZE] for i in range(0, len(file_paths), BATCH_SIZE)]
            
            with ThreadPoolExecutor(max_workers=MAX_WORKER_THREADS) as executor:
                future_to_batch = {executor.submit(calculate_best_records_batch, batch): batch for batch in batches}
                
                for future in as_completed(future_to_batch):
                    try:
                        batch_qps, batch_qps_time, batch_latency, batch_latency_time = future.result()
                        
                        # 合并结果
                        if batch_qps > best_qps:
                            best_qps = batch_qps
                            best_qps_time = batch_qps_time
                        
                        if batch_latency < best_latency and batch_latency != float('inf'):
                            best_latency = batch_latency
                            best_latency_time = batch_latency_time
                            
                    except Exception as e:
                        logger.error(f"批处理失败: {e}")
                        continue
        
        # 更新缓存
        with cache_lock:
            if team_id in team_cache:
                team_cache[team_id].best_records_cached = True
                
    except Exception as e:
        logger.error(f"⚠️ 计算最佳记录失败 (team_id: {team_id}): {e}")
    
    # 如果没有找到有效的延迟数据，设为None
    if best_latency == float('inf'):
        best_latency = None
        best_latency_time = None
    
    return best_qps, best_qps_time, best_latency, best_latency_time

@app.route('/')
def dashboard():
    """Web看板页面"""
    return render_template('dashboard.html')

@app.route('/team/<team_id>/history')
def team_history_page(team_id):
    """团队历史数据查看页面"""
    # 获取团队基本信息
    with data_lock:
        if team_id in teams_data:
            team_data = teams_data[team_id]
            team_name = team_data.team_name
        else:
            # 尝试从文件加载
            file_data = load_team_data(team_id)
            team_name = file_data.get('team_name', f'Team-{team_id}') if file_data else f'Team-{team_id}'
    
    return render_template('team_history.html', team_id=team_id, team_name=team_name)

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
    try:
        # 获取查询参数
        limit = int(request.args.get('limit', 10))  # 默认返回10条
        offset = int(request.args.get('offset', 0))  # 默认从0开始
        
        # 获取历史文件列表
        history_files = get_team_history_files(team_id)
        
        if not history_files:
            return jsonify({
                "message": "No history found for this team",
                "team_id": team_id,
                "history": [],
                "total": 0
            }), 200
        
        # 应用分页
        total = len(history_files)
        paginated_files = history_files[offset:offset + limit]
        
        # 加载数据
        history_data = []
        for file_info in paginated_files:
            try:
                with open(file_info['file_path'], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 添加计算的性能指标
                    metrics = calculate_overall_metrics(data.get('stats', {}))
                    data['metrics'] = metrics
                    history_data.append(data)
            except Exception as e:
                print(f"Error loading {file_info['file_path']}: {e}")
                continue
        
        return jsonify({
            "team_id": team_id,
            "history": history_data,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/teams/<team_id>/history/summary', methods=['GET'])
def get_team_history_summary(team_id):
    """获取团队历史数据摘要（文件数量、时间范围等）"""
    try:
        history_files = get_team_history_files(team_id)
        
        if not history_files:
            return jsonify({
                "team_id": team_id,
                "total_reports": 0,
                "first_report": None,
                "last_report": None,
                "data_directory": f"data/{team_id}"
            })
        
        return jsonify({
            "team_id": team_id,
            "total_reports": len(history_files),
            "first_report": history_files[-1]['timestamp'] if history_files else None,
            "last_report": history_files[0]['timestamp'] if history_files else None,
            "data_directory": f"data/{team_id}",
            "recent_files": [f['filename'] for f in history_files[:5]]  # 最近5个文件
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/cache/status', methods=['GET'])
def get_cache_status_api():
    """获取缓存状态API"""
    try:
        cache_status = get_cache_status()
        total_teams = len(teams_data)
        cached_teams = len([c for c in team_cache.values() if c.best_records_cached])
        
        return jsonify({
            "cache_summary": {
                "total_teams": total_teams,
                "cached_teams": cached_teams,
                "cache_hit_rate": (cached_teams / total_teams * 100) if total_teams > 0 else 0
            },
            "team_cache_details": cache_status,
            "config": {
                "cache_expire_seconds": CACHE_EXPIRE_SECONDS,
                "max_worker_threads": MAX_WORKER_THREADS,
                "batch_size": BATCH_SIZE
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache_api():
    """清理缓存API"""
    try:
        team_id = request.json.get('team_id') if request.json else None
        clear_team_cache(team_id)
        
        if team_id:
            return jsonify({"message": f"团队 {team_id} 缓存已清理"})
        else:
            return jsonify({"message": "所有缓存已清理"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

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
    # 启动时间记录
    start_time = datetime.now()
    
    # # 启动清理线程
    # cleanup_thread = threading.Thread(target=cleanup_inactive_teams, daemon=True)
    # cleanup_thread.start()
    
    logger.info("🚀 启动 BenchBoard 服务器...")
    logger.info(f"   配置: 缓存过期={CACHE_EXPIRE_SECONDS}s, 最大线程={MAX_WORKER_THREADS}, 批大小={BATCH_SIZE}")
    
    try:
        # 启动时加载历史数据（优化版本）
        loaded_count = load_all_teams_on_startup()
        
        # 输出加载统计
        load_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"📊 数据加载完成: {loaded_count} 个团队, 耗时 {load_time:.2f}s")
        
        if loaded_count > 0:
            logger.info(f"💾 缓存状态: {len(team_cache)} 个团队已缓存")
        
        # 启动服务器
        logger.info("🌐 服务器启动中... (0.0.0.0:8080)")
        socketio.run(app, host='0.0.0.0', port=8080, debug=True, allow_unsafe_werkzeug=True)
        
    except Exception as e:
        logger.error(f"❌ 服务器启动失败: {e}")
        raise 
    