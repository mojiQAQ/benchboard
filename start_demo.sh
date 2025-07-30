#!/bin/bash

# BenchBoard 演示启动脚本
# 用于快速启动服务器和多个测试客户端

echo "🚀 启动 BenchBoard 演示系统"
echo "================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
if [ ! -f "requirements.txt" ]; then
    echo "❌ 错误: 未找到 requirements.txt"
    exit 1
fi

# 安装依赖
echo "📥 安装依赖..."
pip3 install -r requirements.txt

# 创建数据目录
mkdir -p data

# 启动服务器
echo "🌐 启动服务器..."
python3 app.py &
SERVER_PID=$!

# 等待服务器启动
echo "⏳ 等待服务器启动..."
sleep 3

# 检查服务器是否启动成功
if ! curl -s http://localhost:8080 > /dev/null; then
    echo "❌ 错误: 服务器启动失败"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "✅ 服务器启动成功: http://localhost:8080"

# 启动测试客户端
echo "🧪 启动测试客户端..."

# 启动第一个客户端
echo "   启动第一小组..."
python3 test_client.py --team-id team1 --team-name "第一小组" --interval 30 &
CLIENT1_PID=$!

# 启动第二个客户端
echo "   启动第二小组..."
python3 test_client.py --team-id team2 --team-name "第二小组" --interval 25 &
CLIENT2_PID=$!

# 启动第三个客户端
echo "   启动第三小组..."
python3 test_client.py --team-id team3 --team-name "第三小组" --interval 35 &
CLIENT3_PID=$!

# 启动第四个客户端
echo "   启动第四小组..."
python3 test_client.py --team-id team4 --team-name "第四小组" --interval 40 &
CLIENT4_PID=$!

# 启动第五个客户端
echo "   启动第五小组..."
python3 test_client.py --team-id team5 --team-name "第五小组" --interval 45 &
CLIENT5_PID=$!

# 启动第六个客户端
echo "   启动第六小组..."
python3 test_client.py --team-id team6 --team-name "第六小组" --interval 50 &
CLIENT6_PID=$!

echo ""
echo "🎉 演示系统启动完成！"
echo "================================"
echo "📊 Web看板: http://localhost:8080"
echo "📝 日志输出:"
echo ""

# 等待用户中断
trap 'cleanup' INT

cleanup() {
    echo ""
    echo "🛑 正在停止演示系统..."
    
    # 停止所有客户端
    kill $CLIENT1_PID $CLIENT2_PID $CLIENT3_PID $CLIENT4_PID $CLIENT5_PID $CLIENT6_PID 2>/dev/null
    
    # 停止服务器
    kill $SERVER_PID 2>/dev/null
    
    echo "✅ 演示系统已停止"
    exit 0
}

# 保持脚本运行
while true; do
    sleep 1
done 