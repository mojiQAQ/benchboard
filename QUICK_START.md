# BenchBoard 快速开始指南

## 🚀 一键启动演示

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动演示系统（包含服务器和6个测试客户端）
./start_demo.sh
```

## 📋 手动启动步骤

### 1. 启动服务器
```bash
python app.py
```

### 2. 访问Web看板
打开浏览器访问: http://localhost:8080

### 3. 启动测试客户端（可选）
```bash
# 终端1 - 第一小组
python test_client.py --team-id team1 --team-name "第一小组" --interval 30

# 终端2 - 第二小组  
python test_client.py --team-id team2 --team-name "第二小组" --interval 25

# 终端3 - 第三小组
python test_client.py --team-id team3 --team-name "第三小组" --interval 35
```

## 🧪 测试API

```bash
# 运行API测试
python test_api.py
```

## 📊 数据格式示例

查看 `example_data.json` 文件了解数据格式要求。

## 🔧 自定义配置

### 修改服务器端口
编辑 `app.py` 文件，修改最后一行：
```python
socketio.run(app, host='0.0.0.0', port=8080, debug=True)
```

### 修改团队数量限制
编辑 `templates/dashboard.html` 文件，修改：
```javascript
const maxTeams = 6;  // 改为你需要的数量
```

## 📱 移动端访问

系统支持移动设备访问，会自动适配屏幕大小。

## 🛠️ 故障排除

### 端口被占用
```bash
# 查看端口占用
lsof -i :8080

# 杀死进程
kill -9 <PID>
```

### 依赖安装失败
```bash
# 升级pip
pip install --upgrade pip

# 重新安装
pip install -r requirements.txt
```

## 📞 获取帮助

- 查看完整文档: `README.md`
- 检查API规范: `openapi.yaml`
- 运行测试: `python test_api.py` 