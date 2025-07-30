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

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务器

```bash
python app.py
```

服务器将在 `http://localhost:8080` 启动

### 3. 访问Web看板

打开浏览器访问 `http://localhost:8080` 即可看到实时看板

### 4. 测试数据上报

使用测试客户端模拟压测工具上报数据：

```bash
# 启动第一个测试客户端
python test_client.py --team-id team1 --team-name "第一小组" --interval 30

# 启动第二个测试客户端（新终端）
python test_client.py --team-id team2 --team-name "第二小组" --interval 25

# 启动第三个测试客户端（新终端）
python test_client.py --team-id team3 --team-name "第三小组" --interval 35
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

## 数据格式

系统严格按照OpenAPI规范处理数据，主要包含以下统计信息：

- **基础统计**: 总运行时间、发送请求数、完成请求数、错误数等
- **操作统计**: 各类操作（传感器数据、读写操作、批量操作、查询）的统计
- **高优先级统计**: 高优先级请求的统计信息
- **性能指标**: QPS、错误率等关键性能指标
- **延迟分析**: 详细的延迟分布统计

## 配置说明

### 环境变量

- `FLASK_ENV`: 运行环境（development/production）
- `FLASK_DEBUG`: 调试模式（True/False）

### 服务器配置

- **端口**: 8080
- **主机**: 0.0.0.0（允许外部访问）
- **WebSocket**: 支持实时通信
- **CORS**: 允许跨域请求

## 文件结构

```
benchboard/
├── app.py                 # 主应用文件
├── requirements.txt       # Python依赖
├── test_client.py        # 测试客户端
├── openapi.yaml          # API规范文档
├── README.md             # 项目说明
├── templates/
│   └── dashboard.html    # Web看板页面
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

2. **依赖安装失败**
   ```bash
   # 升级pip
   pip install --upgrade pip
   # 重新安装依赖
   pip install -r requirements.txt
   ```

3. **WebSocket连接失败**
   - 检查防火墙设置
   - 确认浏览器支持WebSocket
   - 查看浏览器控制台错误信息

## 贡献指南

欢迎提交Issue和Pull Request来改进项目！

## 许可证

MIT License 