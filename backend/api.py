from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
from backend.database import Database
from backend.scraper import PropertyScraper

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

db = Database()
scraper = PropertyScraper()

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

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """手动刷新数据"""
    try:
        result = scraper.fetch_all_properties()
        if result:
            units = result['total_available_units']
            projects = result['total_projects']
            db.save_record(units, projects, result)
            return jsonify({
                'success': True,
                'data': {
                    'available_units': units,
                    'total_projects': projects
                }
            })
        return jsonify({
            'success': False,
            'error': '数据抓取失败'
        }), 500
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"刷新数据时发生错误: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'服务器错误: {error_msg}'
        }), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
