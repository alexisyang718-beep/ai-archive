#!/usr/bin/env python3
"""
定时采集脚本 - 由 crontab 调用，按渠道分别采集

支持两种调度模式：
1. 全量采集：python3 collector_cron.py
2. 单渠道采集：python3 collector_cron.py --channel x/weibo/rss

渠道分频建议（crontab）：
  # X（每 2 小时）- Twitter API不稳定，降低频率减少错误
  0 0,2,4,6,8,10,12,14,16,18,20,22 * * *   python3 collector_cron.py --channel x
  # 微博（每 2 小时）
  15 0,2,4,6,8,10,12,14,16,18,20,22 * * *  python3 collector_cron.py --channel weibo
  # RSS（每 3 小时）
  30 0,3,6,9,12,15,18,21 * * *  python3 collector_cron.py --channel rss

采集完成后发送 macOS 通知 + 渠道状态总览。
"""

import sys
import os
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
V2_ROOT = PROJECT_ROOT / "v2"
SCRIPTS_DIR = V2_ROOT / "scripts"

# 添加 scripts 到 path
sys.path.insert(0, str(SCRIPTS_DIR))


def send_notification(title: str, message: str):
    """发送 macOS 通知"""
    try:
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}" sound name "Submarine"'
        ], check=False, timeout=10)
    except Exception:
        pass


def run_single_channel(channel: str, today: str) -> dict:
    """
    执行单个渠道的采集。
    
    Args:
        channel: 渠道名（x/weibo/rss/web）
        today: 日期 YYYY-MM-DD
        
    Returns:
        {"channel": str, "count": int, "success": bool, "error": str}
    """
    # channel → collector.py 的 --source 参数映射
    source_map = {
        "x": "x",
        "weibo": "weibo",
        "rss": "rss",
        # "search": "web",  # web 源暂未实现，先禁用
    }
    source = source_map.get(channel, channel)
    
    result_info = {
        "channel": channel,
        "count": 0,
        "success": False,
        "error": "",
    }
    
    # 设置环境变量，确保能找到 twitter-cli 等工具
    env = os.environ.copy()
    env["PATH"] = "/Users/yangliu/.local/bin:/Library/Frameworks/Python.framework/Versions/3.13/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
    
    # 使用固定的 Python 路径，避免 crontab 环境问题
    python_exe = "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
    
    try:
        result = subprocess.run(
            [python_exe, str(SCRIPTS_DIR / "collector.py"),
             "--source", source, "--date", today],
            capture_output=True, text=True, timeout=300,  # 5 分钟超时
            env=env
        )
        
        if result.returncode == 0:
            result_info["success"] = True
            # 解析输出中的条数
            for line in result.stdout.split("\n"):
                if "存储" in line and "条" in line:
                    try:
                        count_str = line.split("存储")[1].split("条")[0].strip()
                        result_info["count"] = int(count_str)
                    except (ValueError, IndexError):
                        pass
        else:
            # 收集所有错误信息（stdout 和 stderr 都可能包含错误）
            error_parts = []
            if result.stderr:
                error_parts.append(result.stderr.strip())
            if result.stdout and ("error" in result.stdout.lower() or "exception" in result.stdout.lower() or "traceback" in result.stdout.lower()):
                error_parts.append(result.stdout.strip())
            
            # 记录完整输出到日志文件以便调试
            log_dir = Path("v2/logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            debug_log = log_dir / f"cron_{channel}_debug.log"
            with open(debug_log, "a") as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Return code: {result.returncode}\n")
                f.write(f"STDOUT:\n{result.stdout}\n")
                f.write(f"STDERR:\n{result.stderr}\n")
                f.write(f"{'='*50}\n")
            
            if error_parts:
                result_info["error"] = " | ".join(error_parts)[:300]
            else:
                result_info["error"] = f"退出码 {result.returncode} (详见 cron_{channel}_debug.log)"
            
    except subprocess.TimeoutExpired:
        result_info["error"] = "超时(5min)"
    except Exception as e:
        result_info["error"] = str(e)[:200]
    
    return result_info


def run_all_channels(today: str) -> list:
    """按顺序采集所有渠道（仅x/weibo/rss）"""
    channels = ["x", "weibo", "rss"]  # 移除search
    results = []
    
    for ch in channels:
        print(f"\n{'─'*40}")
        print(f"📡 采集渠道: {ch}")
        print(f"{'─'*40}")
        
        send_notification(f"📡 采集 {ch}", f"正在采集 {ch}...")
        
        info = run_single_channel(ch, today)
        results.append(info)
        
        if info["success"]:
            print(f"  ✅ {ch}: {info['count']} 条")
        else:
            print(f"  ❌ {ch}: {info['error']}")

    return results


def print_channel_status(today: str):
    """打印各渠道的文件状态（直接读文件，不依赖 collector.py）"""
    try:
        from atom_store import AtomStore
        store = AtomStore()
        status = store.get_channel_status(today)
        
        print(f"\n📊 渠道文件状态 ({today}):")
        print(f"{'─'*60}")
        for ch, info in status["channels"].items():
            icon = "✅" if info["exists"] and info["count"] > 0 else "❌" if not info["exists"] else "⚠️"
            cats = ", ".join(f"{k}:{v}" for k, v in sorted(
                info["categories"].items(), key=lambda x: -x[1])[:3])
            print(f"  {icon} {ch:8s} │ {info['count']:4d} 条 │ {cats}")
        if "legacy" in status:
            print(f"  📦 legacy  │ {status['legacy']['count']:4d} 条 │ (旧格式)")
        print(f"{'─'*60}")
        print(f"  合计: {status['total']} 条\n")
    except Exception as e:
        print(f"  ⚠️ 无法获取渠道状态: {e}")


def main():
    parser = argparse.ArgumentParser(description="定时采集（按渠道分别执行）")
    parser.add_argument("--channel", choices=["x", "weibo", "rss", "all"],
                        default="all", help="采集渠道（默认全部）")
    parser.add_argument("--status", action="store_true",
                        help="只查看当前渠道文件状态，不执行采集")
    args = parser.parse_args()
    
    today = datetime.now().strftime("%Y-%m-%d")
    start_time = datetime.now()
    
    # 纯状态查看模式
    if args.status:
        print_channel_status(today)
        return
    
    print(f"\n{'='*50}")
    print(f"🕐 定时采集开始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   模式: {'全渠道' if args.channel == 'all' else args.channel}")
    print(f"{'='*50}")
    
    send_notification("📡 资讯采集", f"开始采集 @ {start_time.strftime('%H:%M')}")
    
    # 执行采集
    if args.channel == "all":
        results = run_all_channels(today)
    else:
        info = run_single_channel(args.channel, today)
        results = [info]
    
    # 统计结果
    end_time = datetime.now()
    duration = (end_time - start_time).seconds
    
    total_count = sum(r["count"] for r in results)
    success_count = sum(1 for r in results if r["success"])
    fail_count = sum(1 for r in results if not r["success"])
    
    # 打印结果
    print(f"\n{'='*50}")
    print(f"✅ 采集完成: {end_time.strftime('%H:%M:%S')} (耗时 {duration}s)")
    print(f"{'='*50}")
    
    for r in results:
        icon = "✅" if r["success"] else "❌"
        count_str = f"{r['count']} 条" if r["success"] else r["error"][:40]
        print(f"  {icon} {r['channel']:8s} │ {count_str}")
    
    print(f"  {'─'*40}")
    print(f"  合计: {total_count} 条 ({success_count}成功/{fail_count}失败)\n")
    
    # 打印渠道文件状态
    print_channel_status(today)
    
    # 发送完成通知
    channel_summary = " | ".join(
        f"{r['channel']}:{'✅' if r['success'] else '❌'}{r['count']}"
        for r in results
    )
    msg = f"{channel_summary} = {total_count}条 ({duration}s)"
    send_notification("✅ 采集完成", msg)
    
    # 如果有错误，额外通知
    for r in results:
        if not r["success"]:
            send_notification(f"⚠️ {r['channel']} 失败", r["error"][:60])


if __name__ == "__main__":
    main()
