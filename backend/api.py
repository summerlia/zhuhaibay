from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
import threading
import urllib.parse
from datetime import datetime
from typing import Dict
from backend.database import Database
from backend.scraper import PropertyScraper

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

db = Database()
scraper = PropertyScraper()

# 用于跟踪刷新任务状态
refresh_lock = threading.Lock()
refresh_status = {
    'is_running': False,
    'start_time': None,
    'end_time': None,
    'error': None,
    'result': None,  # {'projects': int, 'units': int}
    'current_step': None,  # 当前步骤描述
    'logs': []  # 日志信息
}

@app.route('/')
def index():
    """返回前端页面"""
    return send_from_directory(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend'), 'index.html')

@app.route('/api/records', methods=['GET'])
def get_records():
    """获取所有历史记录"""
    try:
        records = db.get_all_records()
        return jsonify({
            'success': True,
            'data': records
        })
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"获取历史记录失败: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'获取数据失败: {error_msg}'
        }), 500

@app.route('/api/latest', methods=['GET'])
def get_latest():
    """获取最新记录"""
    try:
        record = db.get_latest_record()
        return jsonify({
            'success': True,
            'data': record
        })
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"获取最新记录失败: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'获取数据失败: {error_msg}'
        }), 500

@app.route('/api/properties', methods=['GET'])
def get_properties():
    """获取所有楼盘列表"""
    try:
        properties = db.get_property_list()
        return jsonify({
            'success': True,
            'data': properties
        })
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"获取楼盘列表失败: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'获取数据失败: {error_msg}'
        }), 500

@app.route('/api/property/<path:property_name>', methods=['GET'])
def get_property_history(property_name):
    """获取指定楼盘的历史数据"""
    try:
        # Flask 会自动解码 URL，但为了安全再次解码
        property_name = urllib.parse.unquote(property_name)
        history = db.get_property_history(property_name)
        return jsonify({
            'success': True,
            'data': history
        })
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"获取楼盘历史数据失败: {property_name}, 错误: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'获取数据失败: {error_msg}'
        }), 500

@app.route('/api/properties/latest', methods=['GET'])
def get_latest_properties():
    """获取最新的所有楼盘数据"""
    try:
        properties = db.get_latest_properties()
        return jsonify({
            'success': True,
            'data': properties
        })
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"获取最新楼盘数据失败: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'获取数据失败: {error_msg}'
        }), 500

def _add_log(message):
    """添加日志到状态"""
    global refresh_status
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with refresh_lock:
        refresh_status['logs'].append(log_entry)
        # 只保留最近50条日志
        if len(refresh_status['logs']) > 50:
            refresh_status['logs'] = refresh_status['logs'][-50:]

def _update_step(step):
    """更新当前步骤"""
    global refresh_status
    with refresh_lock:
        refresh_status['current_step'] = step
    _add_log(f"步骤: {step}")

def _refresh_task():
    """后台执行数据刷新任务"""
    global refresh_status
    try:
        start_time = datetime.now().isoformat()
        with refresh_lock:
            refresh_status['is_running'] = True
            refresh_status['start_time'] = start_time
            refresh_status['end_time'] = None
            refresh_status['error'] = None
            refresh_status['result'] = None
            refresh_status['current_step'] = '初始化任务'
            refresh_status['logs'] = []
        
        _add_log("开始后台刷新数据...")
        _update_step("正在抓取数据...")
        
        # 创建一个带回调的 scraper 来更新状态
        class StatusScraper(PropertyScraper):
            def fetch_page(self, start: int):
                _update_step(f"正在请求数据 (第 {start} 页)...")
                _add_log(f"开始请求第 {start} 页数据...")
                try:
                    result = super().fetch_page(start)
                    if result:
                        _add_log(f"数据请求成功 (第 {start} 页)")
                    else:
                        _add_log(f"数据请求失败 (第 {start} 页): 返回 None")
                    return result
                except Exception as e:
                    _add_log(f"数据请求异常 (第 {start} 页): {str(e)}")
                    raise
            
            def parse_properties(self, data: Dict):
                _update_step("正在解析数据...")
                _add_log("开始解析楼盘数据...")
                try:
                    result = super().parse_properties(data)
                    if result:
                        _add_log(f"数据解析成功: 找到 {len(result)} 个楼盘")
                    else:
                        _add_log("数据解析失败: 未找到楼盘数据")
                    return result
                except Exception as e:
                    _add_log(f"数据解析异常: {str(e)}")
                    raise
            
            def fetch_all_properties(self):
                _add_log("开始执行 fetch_all_properties...")
                try:
                    result = super().fetch_all_properties()
                    if result:
                        _add_log(f"fetch_all_properties 成功: {result.get('total_projects', 0)} 个项目")
                    else:
                        _add_log("fetch_all_properties 失败: 返回 None")
                    return result
                except Exception as e:
                    _add_log(f"fetch_all_properties 异常: {str(e)}")
                    raise
        
        status_scraper = StatusScraper()
        result = status_scraper.fetch_all_properties()
        
        if not result:
            end_time = datetime.now().isoformat()
            error_msg = '数据抓取失败，未返回有效数据'
            with refresh_lock:
                refresh_status['is_running'] = False
                refresh_status['end_time'] = end_time
                refresh_status['error'] = error_msg
                refresh_status['current_step'] = '数据抓取失败'
            _add_log(error_msg)
            return
        
        units = result['total_available_units']
        projects = result['total_projects']
        
        _add_log(f"数据抓取成功: {projects} 个项目，共 {units} 套")
        _update_step(f"正在保存数据 ({projects} 个项目，{units} 套)...")
        
        # 保存数据到数据库
        _add_log("开始保存数据到数据库...")
        success = db.save_record(units, projects, result)
        
        end_time = datetime.now().isoformat()
        
        if success:
            # 验证数据是否真的保存成功
            latest = db.get_latest_record()
            if latest and latest.get('available_units') == units:
                with refresh_lock:
                    refresh_status['is_running'] = False
                    refresh_status['end_time'] = end_time
                    refresh_status['result'] = {
                        'projects': projects,
                        'units': units
                    }
                    refresh_status['current_step'] = '任务完成'
                _add_log(f"数据保存成功并验证: {projects} 个项目，共 {units} 套")
            else:
                error_msg = f'数据保存验证失败: 保存了 {units} 套，但数据库最新记录是 {latest.get("available_units") if latest else "无"}'
                with refresh_lock:
                    refresh_status['is_running'] = False
                    refresh_status['end_time'] = end_time
                    refresh_status['error'] = error_msg
                    refresh_status['current_step'] = '数据保存验证失败'
                _add_log(error_msg)
        else:
            error_msg = '数据保存到数据库失败'
            with refresh_lock:
                refresh_status['is_running'] = False
                refresh_status['end_time'] = end_time
                refresh_status['error'] = error_msg
                refresh_status['current_step'] = '数据保存失败'
            _add_log(error_msg)
            
    except Exception as e:
        import traceback
        error_msg = str(e)
        end_time = datetime.now().isoformat()
        
        with refresh_lock:
            refresh_status['is_running'] = False
            refresh_status['end_time'] = end_time
            refresh_status['error'] = error_msg
            refresh_status['current_step'] = f'发生错误: {error_msg[:50]}'
        
        _add_log(f"刷新数据时发生错误: {error_msg}")
        _add_log(f"错误详情: {traceback.format_exc()}")

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """手动刷新数据（异步执行）"""
    global refresh_status
    
    # 检查是否正在刷新
    with refresh_lock:
        if refresh_status['is_running']:
            return jsonify({
                'success': False,
                'error': '数据刷新任务正在进行中，请稍后再试',
                'status': refresh_status.copy()
            }), 429
        
        # 启动后台任务
        thread = threading.Thread(target=_refresh_task, daemon=True)
        thread.start()
    
    # 立即返回响应，避免超时
    return jsonify({
        'success': True,
        'message': '数据刷新任务已启动，正在后台处理中',
        'status': refresh_status.copy()
    })

@app.route('/api/refresh/status', methods=['GET'])
def refresh_status_endpoint():
    """获取刷新任务状态"""
    global refresh_status
    with refresh_lock:
        return jsonify({
            'success': True,
            'status': refresh_status.copy()
        })

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
