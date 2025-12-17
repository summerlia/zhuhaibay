import schedule
import time
from datetime import datetime
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.scraper import PropertyScraper
from backend.database import Database

class PropertyScheduler:
    def __init__(self):
        self.scraper = PropertyScraper()
        self.db = Database()
    
    def fetch_and_save(self):
        """抓取并保存数据"""
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始抓取数据...")
        
        result = self.scraper.fetch_all_properties()
        if result:
            units = result['total_available_units']
            projects = result['total_projects']
            success = self.db.save_record(units, projects, result)
            if success:
                print(f"数据已保存: {projects} 个项目，共 {units} 套")
            else:
                print("数据保存失败")
        else:
            print("数据抓取失败")
    
    def run(self):
        """运行定时任务"""
        # 立即执行一次
        self.fetch_and_save()
        
        # 每天9点执行
        schedule.every().day.at("09:00").do(self.fetch_and_save)
        
        print("\n定时任务已启动，每天9:00自动抓取数据")
        print("按 Ctrl+C 停止\n")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次

if __name__ == '__main__':
    scheduler = PropertyScheduler()
    scheduler.run()
