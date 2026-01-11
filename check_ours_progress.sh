#!/bin/bash

# 快速检查 OURS 生成进度

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                     OURS 方法生成进度检查                                  ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

python3 << 'EOF'
from pathlib import Path
from datetime import datetime

# 检查 OURS 报告目录
ours_reports_dir = Path("Myexamples/evaluation_system/batch_results/ours/reports")
if ours_reports_dir.exists():
    reports = sorted(ours_reports_dir.glob("*.md"), key=lambda x: x.stat().st_mtime)
    
    print(f"✅ OURS 已生成报告: {len(reports)}/140 篇")
    print(f"   完成度: {len(reports)/140*100:.1f}%")
    
    if reports:
        if len(reports) > 1:
            first_time = reports[0].stat().st_mtime
            last_time = reports[-1].stat().st_mtime
            elapsed = last_time - first_time
            
            if elapsed > 0:
                rate = len(reports) / (elapsed / 3600)
                remaining = 140 - len(reports)
                eta_hours = remaining / rate if rate > 0 else 0
                
                print(f"\n📊 生成统计:")
                print(f"   耗时: {elapsed/3600:.1f} 小时")
                print(f"   生成速率: {rate:.2f} 篇/小时")
                print(f"   预计剩余: {eta_hours:.1f} 小时")
        
        # 显示最新报告
        latest = reports[-1]
        mtime = datetime.fromtimestamp(latest.stat().st_mtime)
        print(f"\n📄 最新报告: {latest.name}")
        print(f"   时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    print("❌ OURS 报告目录不存在")

# 检查后台进程
print("\n🔍 后台进程状态:")
import os
result = os.system("ps aux | grep 'generate_ours_results' | grep -v grep > /dev/null 2>&1")
if result == 0:
    print("   ✅ 生成进程运行中")
else:
    print("   ⚠️ 生成进程已停止")
EOF

echo ""
