import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from supabase import create_client, Client

class Database:
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        # 从环境变量或参数获取 Supabase 配置
        self.supabase_url = supabase_url or os.environ.get('SUPABASE_URL', 'https://bvylfcasktpgucvdupda.supabase.co')
        self.supabase_key = supabase_key or os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ2eWxmY2Fza3RwZ3VjdmR1cGRhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYxMjg1NDUsImV4cCI6MjA4MTcwNDU0NX0.Ej6_U2xt8u2z_0JXA_B9M1A2-t4BX3Z5EhMTyDNRZBU')
        
        try:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            print(f"成功连接到 Supabase: {self.supabase_url}")
            self.init_db()
        except Exception as e:
            print(f"连接 Supabase 失败: {e}")
            raise
    
    def init_db(self):
        """初始化数据库（Supabase 表需要通过 SQL 编辑器创建，这里只做验证）"""
        try:
            # 尝试查询表是否存在（通过查询来验证）
            self.supabase.table('property_records').select('id').limit(1).execute()
            self.supabase.table('property_details').select('id').limit(1).execute()
            print("数据库表验证成功")
        except Exception as e:
            print(f"数据库表验证失败，请确保在 Supabase 中创建了以下表：")
            print("""
            -- property_records 表
            CREATE TABLE IF NOT EXISTS property_records (
                id BIGSERIAL PRIMARY KEY,
                timestamp TEXT NOT NULL,
                available_units INTEGER NOT NULL,
                total_projects INTEGER DEFAULT 0,
                details JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- property_details 表
            CREATE TABLE IF NOT EXISTS property_details (
                id BIGSERIAL PRIMARY KEY,
                timestamp TEXT NOT NULL,
                property_name TEXT NOT NULL,
                available_units INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- 创建索引
            CREATE INDEX IF NOT EXISTS idx_property_name 
            ON property_details(property_name, timestamp);
            """)
            # 不抛出异常，允许继续运行（表可能已经存在）
    
    def save_record(self, available_units: int, total_projects: int = 0, details: Optional[Dict] = None) -> bool:
        """保存一条记录"""
        try:
            print(f"开始保存记录到 Supabase: {available_units} 套, {total_projects} 个项目")
            timestamp = datetime.now().isoformat()
            
            # 准备主记录数据
            record_data = {
                'timestamp': timestamp,
                'available_units': available_units,
                'total_projects': total_projects,
                'details': details if details else None
            }
            
            print(f"插入主记录: timestamp={timestamp}, units={available_units}, projects={total_projects}")
            
            # 插入主记录
            result = self.supabase.table('property_records').insert(record_data).execute()
            
            if not result.data:
                print("主记录插入失败：返回数据为空")
                return False
            
            print(f"主记录插入成功，ID: {result.data[0].get('id')}")
            
            # 保存每个楼盘的详细数据
            if details and 'properties' in details:
                properties_count = len(details['properties'])
                print(f"开始保存 {properties_count} 个楼盘的详细数据到 Supabase...")
                
                # 批量插入楼盘详细数据
                property_details_list = []
                for prop in details['properties']:
                    property_details_list.append({
                        'timestamp': timestamp,
                        'property_name': prop['name'],
                        'available_units': prop.get('available_units', 0)
                    })
                
                if property_details_list:
                    # 批量插入
                    details_result = self.supabase.table('property_details').insert(property_details_list).execute()
                    saved_count = len(details_result.data) if details_result.data else 0
                    print(f"楼盘详细数据保存完成: {saved_count}/{properties_count}")
                else:
                    print("警告: 没有楼盘详细数据需要保存")
            else:
                print("警告: details 中没有 properties 数据")
            
            print("保存记录成功")
            return True
        except Exception as e:
            import traceback
            print(f"保存记录失败: {e}")
            print(traceback.format_exc())
            return False
    
    def get_all_records(self) -> List[Dict]:
        """获取所有记录"""
        try:
            result = self.supabase.table('property_records')\
                .select('timestamp, available_units, total_projects')\
                .order('timestamp', desc=False)\
                .execute()
            
            if not result.data:
                return []
            
            return [
                {
                    'timestamp': row['timestamp'],
                    'available_units': row['available_units'],
                    'total_projects': row.get('total_projects', 0)
                }
                for row in result.data
            ]
        except Exception as e:
            print(f"获取所有记录失败: {e}")
            return []
    
    def get_latest_record(self) -> Optional[Dict]:
        """获取最新记录"""
        try:
            result = self.supabase.table('property_records')\
                .select('timestamp, available_units, total_projects, details')\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            
            if not result.data or len(result.data) == 0:
                return None
            
            row = result.data[0]
            details = row.get('details')
            
            # 如果 details 是字符串，尝试解析为 JSON
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except:
                    details = None
            
            return {
                'timestamp': row['timestamp'],
                'available_units': row['available_units'],
                'total_projects': row.get('total_projects', 0),
                'details': details
            }
        except Exception as e:
            print(f"获取最新记录失败: {e}")
            return None
    
    def get_property_list(self) -> List[str]:
        """获取所有楼盘名称列表"""
        try:
            result = self.supabase.table('property_details')\
                .select('property_name')\
                .execute()
            
            if not result.data:
                return []
            
            # 使用 set 去重
            property_names = set()
            for row in result.data:
                property_names.add(row['property_name'])
            
            return sorted(list(property_names))
        except Exception as e:
            print(f"获取楼盘列表失败: {e}")
            return []
    
    def get_property_history(self, property_name: str) -> List[Dict]:
        """获取指定楼盘的历史数据"""
        try:
            result = self.supabase.table('property_details')\
                .select('timestamp, available_units')\
                .eq('property_name', property_name)\
                .order('timestamp', desc=False)\
                .execute()
            
            if not result.data:
                return []
            
            return [
                {
                    'timestamp': row['timestamp'],
                    'available_units': row['available_units']
                }
                for row in result.data
            ]
        except Exception as e:
            print(f"获取楼盘历史数据失败: {e}")
            return []
    
    def get_latest_properties(self) -> List[Dict]:
        """获取最新的所有楼盘数据"""
        try:
            # 先获取最新时间戳
            latest_result = self.supabase.table('property_details')\
                .select('timestamp')\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            
            if not latest_result.data or len(latest_result.data) == 0:
                return []
            
            latest_time = latest_result.data[0]['timestamp']
            
            # 获取该时间戳的所有楼盘数据
            result = self.supabase.table('property_details')\
                .select('property_name, available_units')\
                .eq('timestamp', latest_time)\
                .order('property_name', desc=False)\
                .execute()
            
            if not result.data:
                return []
            
            return [
                {
                    'name': row['property_name'],
                    'available_units': row['available_units']
                }
                for row in result.data
            ]
        except Exception as e:
            print(f"获取最新楼盘数据失败: {e}")
            return []
