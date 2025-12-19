#!/usr/bin/env python3
"""
命令行工具：刷新房产数据
使用方法：
    python refresh_data.py
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.scraper import PropertyScraper
from backend.database import Database

def main():
    """主函数：抓取并保存数据"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始刷新数据...")
    print("=" * 60)
    
    try:
        # 初始化
        scraper = PropertyScraper()
        db = Database()
        
        # 抓取数据
        print("正在抓取房产数据...")
        result = scraper.fetch_all_properties()
        
        if not result:
            print("❌ 数据抓取失败")
            sys.exit(1)
        
        units = result['total_available_units']
        projects = result['total_projects']
        
        print(f"✅ 数据抓取成功: {projects} 个项目，共 {units} 套")
        
        # 保存数据
        print("正在保存数据到 Supabase...")
        success = db.save_record(units, projects, result)
        
        if success:
            print(f"✅ 数据保存成功: {projects} 个项目，共 {units} 套")
            print("=" * 60)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 刷新完成")
            sys.exit(0)
        else:
            print("❌ 数据保存失败")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

