import requests
import re
import json
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
import time

class PropertyScraper:
    def __init__(self):
        self.base_url = 'https://fdcjy.zhszjj.com/presalelist'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://fdcjy.zhszjj.com/'
        }
        self.page_size = 1000  # 一次性获取1000条数据
    
    def fetch_page(self, start: int) -> Optional[Dict]:
        """获取单页数据"""
        try:
            params = {
                'keywords': 'presale',
                'tabkey': 'all',
                'searchcode': '',
                'start': start,
                'count': self.page_size
            }
            
            response = requests.get(
                self.base_url, 
                params=params,
                headers=self.headers, 
                timeout=120
            )
            response.raise_for_status()
            
            # 尝试解析JSON响应
            try:
                data = response.json()
                return data
            except json.JSONDecodeError:
                # 如果不是JSON，尝试解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                return {'html': response.text, 'soup': soup}
            
        except requests.RequestException as e:
            print(f"请求第 {start} 页失败: {e}")
            return None
        except Exception as e:
            print(f"解析第 {start} 页失败: {e}")
            return None
    
    def is_valid_property_name(self, name: str) -> bool:
        """验证楼盘名称是否有效"""
        if not name or len(name.strip()) == 0:
            return False
        
        # 过滤垃圾数据
        invalid_patterns = [
            r'^\d{11,}$',  # 纯数字且长度超过10位（如：20230040466）
            r'^/$',  # 只有斜杠
            r'^\d+栋$',  # 只有数字+栋（如：1栋）
            r'^[A-Z0-9]{15,}$',  # 纯大写字母和数字的长串（如：440403004001GB00024）
            r'.*地下室.*车位.*',  # 包含"地下室"和"车位"的（如：B区地下室（车位分割））
            r'^[A-Z]区地下室',  # A区地下室、B区地下室等
            r'^\d{12}[A-Z0-9]+$',  # 数字开头的编码（如：440403004001GB00024）
        ]
        
        for pattern in invalid_patterns:
            if re.match(pattern, name, re.IGNORECASE):
                return False
        
        return True
    
    def parse_properties(self, data: Dict) -> List[Dict]:
        """解析房产数据"""
        properties = []
        
        # 如果是JSON格式
        if 'data' in data or 'list' in data or 'items' in data:
            items = data.get('data', data.get('list', data.get('items', [])))
            for item in items:
                name = item.get('projectName', item.get('name', ''))
                
                # 验证名称有效性
                if not self.is_valid_property_name(name):
                    continue
                
                prop = {
                    'name': name,
                    'available_units': item.get('availableUnits', item.get('saleCount', 0)),
                    'total_units': item.get('totalUnits', item.get('totalCount', 0)),
                    'developer': item.get('developer', item.get('company', '')),
                    'district': item.get('district', item.get('area', ''))
                }
                properties.append(prop)
        
        # 如果是HTML格式
        elif 'soup' in data:
            soup = data['soup']
            
            # 查找所有包含房产信息的div容器
            house_containers = soup.find_all('div', class_='house-info')
            
            for container in house_containers:
                try:
                    # 提取项目名称 - 在a标签中
                    name_elem = container.find('a', class_='overflow')
                    name = name_elem.get_text(strip=True) if name_elem else ''
                    
                    # 验证名称有效性
                    if not self.is_valid_property_name(name):
                        continue
                    
                    # 提取待售套数 - 在house-info-main的表格中
                    info_main = container.find('div', class_='house-info-main')
                    if info_main:
                        text = info_main.get_text()
                        match = re.search(r'待售[：:\s]*(\d+)', text)
                        
                        if match:
                            available_units = int(match.group(1))
                            prop = {
                                'name': name,
                                'available_units': available_units
                            }
                            properties.append(prop)
                except Exception as e:
                    continue
        
        return properties
    
    def fetch_all_properties(self) -> Optional[Dict]:
        """获取所有房产数据"""
        print("开始抓取珠海所有在售房产数据...")
        print("正在获取数据（一次性获取1000条）...")
        
        # 一次性获取1000条数据
        data = self.fetch_page(1)
        if not data:
            print("数据获取失败")
            return None
        
        properties = self.parse_properties(data)
        
        if not properties:
            print("未找到房产数据")
            return None
        
        total_available = sum(p.get('available_units', 0) for p in properties)
        
        print(f"\n抓取完成！共 {len(properties)} 个项目，总待售 {total_available} 套")
        
        return {
            'total_projects': len(properties),
            'total_available_units': total_available,
            'properties': properties
        }
    
    def fetch_available_units(self) -> Optional[int]:
        """获取总待售套数（保持向后兼容）"""
        result = self.fetch_all_properties()
        if result:
            return result['total_available_units']
        return None
