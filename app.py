"""
Flask Web应用主文件
"""

import os
import logging
from flask import Flask, render_template, jsonify, request
import yaml

from src.threadpool_manager import ThreadPoolManager
from src.threadpool_manager.exceptions import (
    PoolNotFoundError, 
    TaskNotFoundError, 
    PoolAlreadyExistsError
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)

# 加载配置
def load_config():
    """加载配置文件"""
    config_path = 'custom-conf.yml'
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

config = load_config()
app.config.update(config.get('flask', {}))

# 创建线程池管理器实例
pool_manager = ThreadPoolManager()

# 根路由
@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

# API路由 - 线程池管理
@app.route('/api/pools', methods=['GET'])
def list_pools():
    """获取线程池列表"""
    try:
        pools = pool_manager.list_pools()
        return jsonify({'success': True, 'data': pools})
    except Exception as e:
        logger.error(f"Error listing pools: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pools', methods=['POST'])
def create_pool():
    """创建线程池"""
    try:
        data = request.get_json()
        name = data.get('name')
        max_workers = int(data.get('max_workers', 5))
        
        pool_id = pool_manager.create_pool(name=name, max_workers=max_workers)
        pool_info = pool_manager.get_pool(pool_id).get_info()
        
        return jsonify({'success': True, 'data': pool_info})
    except PoolAlreadyExistsError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating pool: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
# 停止线程池未执行future
@app.route('/api/pools/<pool_id>/cancel_pool_tasks', methods=['POST'])
def cancel_pool_tasks(pool_id):
    """停止线程池未执行future"""
    try:
        success = pool_manager.cancel_pool_tasks(pool_id)
        return jsonify({'success': success})
    except PoolNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error canceling tasks in pool {pool_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

    


@app.route('/api/pools/<pool_id>', methods=['DELETE'])
def close_pool(pool_id):
    """关闭线程池"""
    try:
        success = pool_manager.close_pool(pool_id, wait=True)
        return jsonify({'success': success})
    except PoolNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error closing pool {pool_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pools/<pool_id>/force-close', methods=['DELETE'])
def force_close_pool(pool_id):
    """强制关闭线程池"""
    try:
        cancelled_tasks = pool_manager.force_close_pool(pool_id)
        return jsonify({
            'success': True, 
            'cancelled_tasks': cancelled_tasks
        })
    except PoolNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error force closing pool {pool_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# API路由 - 任务管理
@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    """获取任务列表（支持分页）"""
    try:
        pool_id = request.args.get('pool_id')
        
        # 分页参数
        try:
            page = max(1, int(request.args.get('page', 1)))
            per_page = max(1, min(100, int(request.args.get('per_page', 10))))
        except (ValueError, TypeError):
            page = 1
            per_page = 10
        
        # 获取所有任务
        all_tasks = pool_manager.list_tasks(pool_id=pool_id)
        
        # 分页计算
        total_items = len(all_tasks)
        total_pages = max(1, (total_items + per_page - 1) // per_page)
        current_page = max(1, min(page, total_pages))
        
        # 计算当前页数据
        start_index = (current_page - 1) * per_page
        end_index = start_index + per_page
        current_tasks = all_tasks[start_index:end_index]
        
        # 构建分页元数据
        pagination = {
            'current_page': current_page,
            'per_page': per_page,
            'total_items': total_items,
            'total_pages': total_pages,
            'has_next': current_page < total_pages,
            'has_prev': current_page > 1,
            'start_item': start_index + 1 if total_items > 0 else 0,
            'end_item': min(current_page * per_page, total_items)
        }
        
        return jsonify({
            'success': True, 
            'data': current_tasks,
            'pagination': pagination
        })
        
    except PoolNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
def submit_task():
    """提交任务"""
    try:
        data = request.get_json()
        pool_id = data.get('pool_id')
        task_name = data.get('task_name')
        task_type = data.get('task_type', 'demo')
        
        # 创建演示任务
        if task_type == 'demo':
            import time
            def demo_task(duration=5):
                time.sleep(duration)
                return f"Task completed after {duration} seconds"
            
            # 安全地转换duration参数为整数
            duration_str = data.get('duration', '5')
            try:
                duration = int(str(duration_str))
            except (ValueError, TypeError):
                duration = 5
                logger.warning(f"Invalid duration value: {duration_str}, using default: 5")
            
            task_id = pool_manager.submit_task(
                pool_id, demo_task, task_name, duration
            )
        else:
            return jsonify({'success': False, 'error': 'Unsupported task type'}), 400
        
        return jsonify({'success': True})
        
    except PoolNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error submitting task: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def cancel_task(task_id):
    """取消任务"""
    try:
        success = pool_manager.cancel_task(task_id)
        return jsonify({'success': success})
    except TaskNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取任务详情"""
    try:
        task = pool_manager.get_task(task_id)
        return jsonify({'success': True, 'data': task.get_info()})
    except TaskNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 系统信息
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取系统统计信息"""
    try:
        stats = pool_manager.get_stats()
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500



@app.route('/api/pools/<pool_id>/resize', methods=['PUT'])
def resize_pool(pool_id):
    """
    动态调整线程池大小
    
    请求体:
    {
        "max_workers": 10  # 新的最大工作线程数
    }
    
    返回:
    {
        "success": true,
        "message": "调整成功",
        "data": {调整结果详情}
    }
    """
    try:
        data = request.get_json()
        if not data or 'max_workers' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必要参数: max_workers'
            }), 400
        
        new_max_workers = int(data['max_workers'])
        
        # 调用线程池管理器调整大小
        result = pool_manager.resize_pool(pool_id, new_max_workers)
        
        return jsonify({
            'success': result['success'],
            'message': result['message'],
            'data': result
        })
        
    except KeyError as e:
        return jsonify({
            'success': False,
            'error': f'线程池不存在: {str(e)}'
        }), 404
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'参数错误: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"Error resizing pool {pool_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'调整线程池大小失败: {str(e)}'
        }), 500

@app.route('/api/pools/<pool_id>/resize-info', methods=['GET'])
def get_pool_resize_info(pool_id):
    """
    获取线程池调整大小的相关信息
    
    返回:
    {
        "success": true,
        "data": {
            "pool_id": "pool-1",
            "name": "测试线程池",
            "current_max_workers": 5,
            "active_tasks": 3,
            "can_resize": true,
            "status": "running",
            "suggested_max_workers": 5
        }
    }
    """
    try:
        info = pool_manager.get_pool_resize_info(pool_id)
        return jsonify({
            'success': True,
            'data': info
        })
        
    except KeyError as e:
        return jsonify({
            'success': False,
            'error': f'线程池不存在: {str(e)}'
        }), 404
    except Exception as e:
        logger.error(f"Error getting resize info for pool {pool_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'获取调整信息失败: {str(e)}'
        }), 500

# 应用生命周期
with app.app_context():
    logger.info("ThreadPoolManager Web应用启动")
    
    # 创建默认线程池
    try:
        default_pool_id = pool_manager.create_pool("default", 5)
        logger.info(f"Created default pool: {default_pool_id}")
    except PoolAlreadyExistsError:
        logger.warning("Default pool already exists")
    except Exception as e:
        logger.error(f"Error creating default pool: {e}")



if __name__ == '__main__':
    import atexit
    @atexit.register
    def cleanup():
        """应用退出时清理资源"""
        logger.info("正在关闭应用...")
        pool_manager.shutdown()
    # 运行应用
    host = config.get('flask', {}).get('host', '127.0.0.1')
    port = config.get('flask', {}).get('port', 5000)
    debug = config.get('flask', {}).get('debug', True)
    
    app.run(host=host, port=port, debug=debug)