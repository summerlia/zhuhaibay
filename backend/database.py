import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

class Database:
    def __init__(self, db_path: str = None):
        # 优先使用环境变量，如果没有则自动检测持久化磁盘路径
        if db_path is None:
            db_path = os.environ.get('DB_PATH')
            
        if db_path is None:
            # 检查 Render 持久化磁盘路径
            render_disk_path = '/opt/render/project/src/data/properties.db'
            if os.path.exists('/opt/render/project/src/data'):
                db_path = render_disk_path
            else:
                # 本地开发路径
                db_path = 'data/properties.db'
        
        self.db_path = db_path
        # 确保目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        self.init_db()
    
    def init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 主记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS property_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                available_units INTEGER NOT NULL,
                total_projects INTEGER DEFAULT 0,
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 楼盘详细记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS property_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                property_name TEXT NOT NULL,
                available_units INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_property_name 
            ON property_details(property_name, timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    def save_record(self, available_units: int, total_projects: int = 0, details: Optional[Dict] = None) -> bool:
        """保存一条记录"""
        try:
            print(f"开始保存记录: {available_units} 套, {total_projects} 个项目")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            timestamp = datetime.now().isoformat()
            details_json = json.dumps(details, ensure_ascii=False) if details else None
            
            print(f"插入主记录: timestamp={timestamp}, units={available_units}, projects={total_projects}")
            cursor.execute(
                'INSERT INTO property_records (timestamp, available_units, total_projects, details) VALUES (?, ?, ?, ?)',
                (timestamp, available_units, total_projects, details_json)
            )
            
            # 保存每个楼盘的详细数据
            if details and 'properties' in details:
                properties_count = len(details['properties'])
                print(f"开始保存 {properties_count} 个楼盘的详细数据...")
                saved_count = 0
                for prop in details['properties']:
                    try:
                        cursor.execute(
                            'INSERT INTO property_details (timestamp, property_name, available_units) VALUES (?, ?, ?)',
                            (timestamp, prop['name'], prop['available_units'])
                        )
                        saved_count += 1
                    except Exception as e:
                        print(f"保存楼盘 {prop.get('name', '未知')} 失败: {e}")
                        continue
                print(f"楼盘详细数据保存完成: {saved_count}/{properties_count}")
            else:
                print("警告: details 中没有 properties 数据")
            
            conn.commit()
            print("数据库提交成功")
            conn.close()
            print("保存记录成功")
            return True
        except Exception as e:
            import traceback
            print(f"保存记录失败: {e}")
            print(traceback.format_exc())
            return False
    
    def get_all_records(self) -> List[Dict]:
        """获取所有记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT timestamp, available_units, total_projects FROM property_records ORDER BY timestamp')
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'timestamp': row[0], 
                'available_units': row[1],
                'total_projects': row[2] if len(row) > 2 else 0
            }
            for row in rows
        ]
    
    def get_latest_record(self) -> Optional[Dict]:
        """获取最新记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT timestamp, available_units, total_projects, details FROM property_records ORDER BY timestamp DESC LIMIT 1')
        row = cursor.fetchone()
        conn.close()
        
        if row:
            details = None
            if row[3]:
                try:
                    details = json.loads(row[3])
                except:
                    pass
            
            return {
                'timestamp': row[0], 
                'available_units': row[1],
                'total_projects': row[2] if len(row) > 2 else 0,
                'details': details
            }
        return None
    
    def get_property_list(self) -> List[str]:
        """获取所有楼盘名称列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT property_name FROM property_details ORDER BY property_name')
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    
    def get_property_history(self, property_name: str) -> List[Dict]:
        """获取指定楼盘的历史数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT timestamp, available_units FROM property_details WHERE property_name = ? ORDER BY timestamp',
            (property_name,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {'timestamp': row[0], 'available_units': row[1]}
            for row in rows
        ]
    
    def get_latest_properties(self) -> List[Dict]:
        """获取最新的所有楼盘数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取最新时间戳
        cursor.execute('SELECT MAX(timestamp) FROM property_details')
        latest_time = cursor.fetchone()[0]
        
        if not latest_time:
            conn.close()
            return []
        
        # 获取该时间戳的所有楼盘数据
        cursor.execute(
            'SELECT property_name, available_units FROM property_details WHERE timestamp = ? ORDER BY property_name',
            (latest_time,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {'name': row[0], 'available_units': row[1]}
            for row in rows
        ]
