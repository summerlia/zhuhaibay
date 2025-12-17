from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
import threading
from datetime import datetime
from backend.database import Database
from backend.scraper import PropertyScraper

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

db = Database()
scraper = PropertyScraper()

# 用于跟踪刷新任务状态
refresh_lock = threading.Lock()
is_refreshing = False
last_refresh_time = None

@app.route('/')
def index():
    """返回前端页面"""
    return send_from_directory(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend'), 'index.html')

@app.route('/api/records', methods=['GET'])
def get_records():
    """获取所有历史记录"""
    records = db.get_all_records()
    return jsonify({
        'success': True,
        'data': records
    })

@app.route('/api/latest', methods=['GET'])
def get_latest():
    """获取最新记录"""
    record = db.get_latest_record()
    return jsonify({
        'success': True,
        'data': record
    })

@app.route('/api/properties', methods=['GET'])
def get_properties():
    """获取所有楼盘列表"""
    properties = db.get_property_list()
    return jsonify({
        'success': True,
        'data': properties
    })

@app.route('/api/property/<property_name>', methods=['GET'])
def get_property_history(property_name):
    """获取指定楼盘的历史数据"""
    history = db.get_property_history(property_name)
    return jsonify({
        'success': True,
        'data': history
    })

@app.route('/api/properties/latest', methods=['GET'])
def get_latest_properties():
    """获取最新的所有楼盘数据"""
    properties = db.get_latest_properties()
    return jsonify({
        'success': True,
        'data': properties
    })

def _refresh_task():
    """后台执行数据刷新任务"""
    global is_refreshing, last_refresh_time
    try:
        print(f"[{datetime.now().isoformat()}] 开始后台刷新数据...")
        result = scraper.fetch_all_properties()
        if result:
            units = result['total_available_units']
            projects = result['total_projects']
            db.save_record(units, projects, result)
            last_refresh_time = datetime.now().isoformat()
            print(f"[{datetime.now().isoformat()}] 数据刷新完成: {projects} 个项目，共 {units} 套")
        else:
            print(f"[{datetime.now().isoformat()}] 数据抓取失败")
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"[{datetime.now().isoformat()}] 刷新数据时发生错误: {error_msg}")
        print(traceback.format_exc())
    finally:
        with refresh_lock:
            is_refreshing = False

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """手动刷新数据（异步执行）"""
    global is_refreshing
    
    # 检查是否正在刷新
    with refresh_lock:
        if is_refreshing:
            return jsonify({
                'success': False,
                'error': '数据刷新任务正在进行中，请稍后再试',
                'is_running': True
            }), 429
        
        # 启动后台任务
        is_refreshing = True
        thread = threading.Thread(target=_refresh_task, daemon=True)
        thread.start()
    
    # 立即返回响应，避免超时
    return jsonify({
        'success': True,
        'message': '数据刷新任务已启动，正在后台处理中',
        'is_running': True
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
