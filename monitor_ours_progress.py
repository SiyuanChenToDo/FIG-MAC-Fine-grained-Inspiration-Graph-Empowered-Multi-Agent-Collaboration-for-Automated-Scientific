#!/usr/bin/env python3
"""
监控 OURS 流程的进度
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime

def monitor_progress():
    """监控生成进度"""
    output_dir = Path("Myexamples/evaluation_system/batch_results/ours")
    reports_dir = output_dir / "reports"
    
    print("="*80)
    print("📊 OURS 流程进度监控")
    print("="*80)
    
    while True:
        # 检查报告数
        if reports_dir.exists():
            reports = list(reports_dir.glob("*.md"))
            print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"✅ 已生成报告数: {len(reports)}/140")
            
            if len(reports) > 0:
                # 显示最近生成的报告
                latest = sorted(reports, key=lambda x: x.stat().st_mtime)[-1]
                print(f"📄 最新报告: {latest.name}")
                print(f"   修改时间: {datetime.fromtimestamp(latest.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 检查生成记录
        records_file = output_dir / "generation_records.json"
        if records_file.exists():
            with open(records_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
            
            success_count = sum(1 for r in records if r.get('success'))
            failed_count = sum(1 for r in records if not r.get('success'))
            
            print(f"\n📈 生成统计:")
            print(f"   成功: {success_count}")
            print(f"   失败: {failed_count}")
            print(f"   总计: {len(records)}")
            
            if len(records) >= 140:
                print("\n✅ 生成完成！")
                break
        
        # 等待后重新检查
        time.sleep(30)

if __name__ == "__main__":
    monitor_progress()
