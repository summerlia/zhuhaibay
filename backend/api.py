from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
import threading
import urllib.parse
from datetime import datetime
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
    'result': None  # {'projects': int, 'units': int}
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
        
        print(f"[{start_time}] 开始后台刷新数据...")
        result = scraper.fetch_all_properties()
        
        end_time = datetime.now().isoformat()
        
        if result:
            units = result['total_available_units']
            projects = result['total_projects']
            db.save_record(units, projects, result)
            
            with refresh_lock:
                refresh_status['is_running'] = False
                refresh_status['end_time'] = end_time
                refresh_status['result'] = {
                    'projects': projects,
                    'units': units
                }
            
            print(f"[{end_time}] 数据刷新完成: {projects} 个项目，共 {units} 套")
        else:
            with refresh_lock:
                refresh_status['is_running'] = False
                refresh_status['end_time'] = end_time
                refresh_status['error'] = '数据抓取失败，未返回有效数据'
            print(f"[{end_time}] 数据抓取失败")
    except Exception as e:
        import traceback
        error_msg = str(e)
        end_time = datetime.now().isoformat()
        
        with refresh_lock:
            refresh_status['is_running'] = False
            refresh_status['end_time'] = end_time
            refresh_status['error'] = error_msg
        
        print(f"[{end_time}] 刷新数据时发生错误: {error_msg}")
        print(traceback.format_exc())

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
