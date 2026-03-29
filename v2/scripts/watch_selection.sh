#!/bin/bash
#
# 选题报告实时刷新管理脚本
#
# 用法:
#   ./watch_selection.sh start      # 启动定时刷新（后台）
#   ./watch_selection.sh stop       # 停止定时刷新
#   ./watch_selection.sh status     # 查看状态
#   ./watch_selection.sh once       # 立即生成一次报告
#   ./watch_selection.sh log        # 查看日志

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
V2_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$V2_ROOT/.selection_watch.pid"
LOG_FILE="$V2_ROOT/.selection_watch.log"
REPORT_DIR="$V2_ROOT/docs/daily/$(date +%Y-%m-%d)"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

start_watch() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  定时刷新已在运行 (PID: $(cat "$PID_FILE"))${NC}"
        echo "使用 './watch_selection.sh log' 查看日志"
        return 1
    fi
    
    echo -e "${GREEN}🚀 启动选题报告定时刷新...${NC}"
    
    # 后台运行 Python 脚本
    nohup python3 "$SCRIPT_DIR/generate_selection_report.py" --watch --interval 300 > "$LOG_FILE" 2>&1 &
    
    # 保存 PID
    echo $! > "$PID_FILE"
    
    sleep 1
    
    if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo -e "${GREEN}✅ 已启动 (PID: $(cat "$PID_FILE"))${NC}"
        echo "📁 报告位置: $REPORT_DIR/selection_report.md"
        echo "📋 日志文件: $LOG_FILE"
        echo ""
        echo "常用命令:"
        echo "  ./watch_selection.sh status  # 查看状态"
        echo "  ./watch_selection.sh log     # 查看日志"
        echo "  ./watch_selection.sh stop    # 停止刷新"
    else
        echo -e "${RED}❌ 启动失败${NC}"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop_watch() {
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${YELLOW}⚠️  定时刷新未运行${NC}"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${YELLOW}🛑 停止定时刷新 (PID: $PID)...${NC}"
        kill "$PID" 2>/dev/null
        sleep 1
        
        # 强制终止如果还在运行
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID" 2>/dev/null
        fi
        
        echo -e "${GREEN}✅ 已停止${NC}"
    else
        echo -e "${YELLOW}⚠️  进程已不存在${NC}"
    fi
    
    rm -f "$PID_FILE"
}

check_status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo -e "${GREEN}✅ 定时刷新运行中 (PID: $PID)${NC}"
            echo "📁 报告位置: $REPORT_DIR/selection_report.md"
            echo "📋 日志文件: $LOG_FILE"
            
            # 显示最后更新时间
            if [ -f "$REPORT_DIR/selection_report.md" ]; then
                echo "📝 最后更新: $(stat -f %Sm "$REPORT_DIR/selection_report.md" 2>/dev/null || stat -c %y "$REPORT_DIR/selection_report.md" 2>/dev/null)"
            fi
        else
            echo -e "${RED}❌ 进程已停止，但 PID 文件存在${NC}"
            rm -f "$PID_FILE"
        fi
    else
        echo -e "${YELLOW}⏹️  定时刷新未运行${NC}"
        
        # 显示报告是否存在
        if [ -f "$REPORT_DIR/selection_report.md" ]; then
            echo "📄 现有报告: $REPORT_DIR/selection_report.md"
            echo "📝 最后更新: $(stat -f %Sm "$REPORT_DIR/selection_report.md" 2>/dev/null || stat -c %y "$REPORT_DIR/selection_report.md" 2>/dev/null)"
        fi
    fi
}

generate_once() {
    echo -e "${GREEN}📝 生成选题报告...${NC}"
    python3 "$SCRIPT_DIR/generate_selection_report.py"
}

show_log() {
    if [ -f "$LOG_FILE" ]; then
        echo -e "${GREEN}📋 日志内容 (最后 50 行):${NC}"
        echo "---"
        tail -n 50 "$LOG_FILE"
    else
        echo -e "${YELLOW}⚠️  日志文件不存在${NC}"
    fi
}

# 主逻辑
case "${1:-}" in
    start)
        start_watch
        ;;
    stop)
        stop_watch
        ;;
    status)
        check_status
        ;;
    once)
        generate_once
        ;;
    log)
        show_log
        ;;
    *)
        echo "选题报告实时刷新管理"
        echo ""
        echo "用法: ./watch_selection.sh <命令>"
        echo ""
        echo "命令:"
        echo "  start   启动定时刷新（每5分钟自动更新）"
        echo "  stop    停止定时刷新"
        echo "  status  查看当前状态"
        echo "  once    立即生成一次报告"
        echo "  log     查看运行日志"
        echo ""
        echo "示例:"
        echo "  ./watch_selection.sh start   # 启动后台刷新"
        echo "  ./watch_selection.sh status  # 查看状态"
        echo "  ./watch_selection.sh stop    # 停止刷新"
        ;;
esac
