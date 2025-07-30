# BenchBoard - 压测结果看板

一个基于Python Flask的实时压测结果监控系统，支持多团队同时进行压测并实时展示结果。

## 功能特性

- 🚀 **实时监控**: 基于WebSocket的实时数据更新
- 👥 **多团队支持**: 支持最多6个团队同时展示
- 📊 **数据持久化**: 自动保存压测结果到本地文件
- 🎨 **美观界面**: 现代化的响应式Web界面
- 🔄 **自动清理**: 自动清理不活跃的团队数据
- 📱 **移动适配**: 支持移动设备访问

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   压测工具      │    │   BenchBoard    │    │   Web看板       │
│   (各团队)      │───▶│   HTTP Server   │───▶│   (实时展示)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   本地文件存储   │
                       │   (JSON格式)    │
                       └─────────────────┘
```

## 快速开始

### 1. 创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate

# Windows:
# venv\Scripts\activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动服务器

```bash
# 使用完整版服务器（支持WebSocket实时更新）
python app.py

# 或使用简化版服务器（更稳定）
python simple_app.py
```

服务器将在 `http://localhost:8080` 启动（简化版使用8080端口）

### 4. 访问Web看板

打开浏览器访问相应端口即可看到实时看板

### 5. 测试数据上报

使用测试客户端模拟压测工具上报数据：

```bash
# 启动第一个测试客户端
python test_client.py --team-id team1 --team-name "第一小组" --interval 30

# 启动第二个测试客户端（新终端）
python test_client.py --team-id team2 --team-name "第二小组" --interval 25

# 启动第三个测试客户端（新终端）
python test_client.py --team-id team3 --team-name "第三小组" --interval 35

# 或者使用快速演示脚本
python quick_test.py
```

### 6. 退出虚拟环境

```bash
deactivate
```

## API接口

### 上报压测结果

**POST** `/api/stats/report`

**请求头:**
```
Content-Type: application/json
X-Team-ID: <团队ID>
X-Team-Name: <团队名称>
```

**请求体:** 符合OpenAPI规范的JSON数据

**响应:**
```json
{
  "message": "Stats submitted successfully",
  "team_id": "team1"
}
```

### 获取团队列表

**GET** `/api/teams`

**响应:**
```json
[
  {
    "team_id": "team1",
    "team_name": "第一小组",
    "last_update": "2024-01-01T12:00:00",
    "is_active": true
  }
]
```

### 获取团队统计数据

**GET** `/api/teams/<team_id>`

**响应:**
```json
{
  "team_id": "team1",
  "team_name": "第一小组",
  "last_update": "2024-01-01T12:00:00",
  "stats": { ... }
}
```

### 获取团队历史数据

**GET** `/api/teams/<team_id>/history`

**查询参数:**
- `limit`: 返回数量限制（默认10）
- `offset`: 偏移量（默认0）

**响应:**
```json
{
  "team_id": "team1",
  "history": [
    {
      "team_id": "team1",
      "team_name": "第一小组",
      "timestamp": "2024-01-01T12:00:00",
      "stats": { ... },
      "metrics": { 
        "avg_latency": 45.2,
        "p99_latency": 156.8,
        "high_priority_latency": 32.1,
        "data_loss_rate": 0.5  // 失败率(%)
      }
    }
  ],
  "total": 15,
  "limit": 10,
  "offset": 0,
  "has_more": true
}
```

### 获取团队历史数据摘要

**GET** `/api/teams/<team_id>/history/summary`

**响应:**
```json
{
  "team_id": "team1",
  "total_reports": 15,
  "first_report": "2024-01-01T10:00:00",
  "last_report": "2024-01-01T12:00:00",
  "data_directory": "data/team1",
  "recent_files": ["20240101_120000_123.json", "..."]
}
```

## 数据格式

系统严格按照OpenAPI规范处理数据，主要包含以下统计信息：

- **基础统计**: 总运行时间、发送请求数、完成请求数、错误数等
- **操作统计**: 各类操作（传感器数据、读写操作、批量操作、查询）的统计
- **高优先级统计**: 高优先级请求的统计信息
- **性能指标**: QPS、错误率、延迟分析等关键性能指标
- **最佳记录**: 自动记录最佳QPS和延迟表现及其时间戳

### 数据存储结构

每个团队的数据按以下结构存储：

```
data/
├── team1/                          # 团队目录
│   ├── 20250730_155133_359.json   # 时间戳命名的历史数据
│   ├── 20250730_155138_636.json   # 每次上报都单独保存
│   ├── 20250730_155146_122.json   # 精确到毫秒
│   └── latest.json                 # 最新数据快速访问
├── team2/                          # 其他团队...
└── ...
```

**时间戳格式**: `YYYYMMDD_HHMMSS_fff` (年月日_时分秒_毫秒)

## 配置说明

### 环境变量

- `FLASK_ENV`: 运行环境（development/production）
- `FLASK_DEBUG`: 调试模式（True/False）

### 服务器配置

- **完整版服务器** (`app.py`):
  - 端口: 8080
  - 支持WebSocket实时更新
  - 支持最佳成绩记录
  - 完整的性能指标计算

- **简化版服务器** (`simple_app.py`):
  - 端口: 8080
  - 更稳定，适合演示
  - 基本的性能指标显示
  - 无WebSocket依赖

- **主机**: 0.0.0.0（允许外部访问）
- **CORS**: 允许跨域请求

## 文件结构

```
benchboard/
├── app.py                 # 主应用文件（完整版，支持WebSocket）
├── simple_app.py          # 简化版服务器（更稳定）
├── requirements.txt       # Python依赖
├── test_client.py        # 测试客户端
├── test_api.py           # API测试脚本
├── quick_test.py         # 快速演示脚本
├── openapi.yaml          # API规范文档
├── example_data.json     # 示例数据格式
├── README.md             # 项目说明
├── QUICK_START.md        # 快速开始指南
├── start_demo.sh         # 一键演示脚本
├── templates/
│   └── dashboard.html    # Web看板页面（完整版）
├── venv/                 # 虚拟环境目录（需手动创建）
└── data/                 # 数据存储目录（自动创建）
    ├── team1.json
    ├── team2.json
    └── ...
```

## 使用场景

1. **多团队压测**: 多个开发团队同时进行性能测试
2. **实时监控**: 实时查看各团队的压测进度和结果
3. **数据对比**: 对比不同团队的压测结果
4. **历史追踪**: 保存历史压测数据供后续分析

## 扩展功能

- [ ] 数据导出功能
- [ ] 图表可视化
- [ ] 告警通知
- [ ] 用户认证
- [ ] 数据库存储

## 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 查看端口占用
   lsof -i :8080
   # 杀死进程
   kill -9 <PID>
   ```

2. **虚拟环境问题**
   ```bash
   # 如果虚拟环境创建失败
   python3 -m pip install --upgrade pip
   python3 -m venv venv --clear
   
   # 确认虚拟环境已激活（命令行前应显示 (venv)）
   which python  # 应指向 venv 目录
   
   # 重新激活虚拟环境
   source venv/bin/activate  # macOS/Linux
   # 或 venv\Scripts\activate  # Windows
   ```

3. **依赖安装失败**
   ```bash
   # 升级pip
   pip install --upgrade pip
   # 重新安装依赖
   pip install -r requirements.txt
   ```

4. **中文编码问题**
   ```bash
   # 设置环境变量
   export PYTHONIOENCODING=utf-8
   export LC_ALL=en_US.UTF-8
   ```

5. **WebSocket连接失败**（仅完整版服务器）
   - 检查防火墙设置
   - 确认浏览器支持WebSocket
   - 查看浏览器控制台错误信息
   - 尝试使用简化版服务器：`python simple_app.py`

### 快速验证

```bash
# 验证Python环境
python --version

# 验证依赖安装
python -c "import flask; import requests; print('Dependencies OK')"

# 运行快速测试
python quick_test.py
```

## 贡献指南

欢迎提交Issue和Pull Request来改进项目！

## 许可证

MIT License 