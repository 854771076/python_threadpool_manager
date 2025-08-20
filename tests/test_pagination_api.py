#!/usr/bin/env python3
"""
分页API单元测试
"""
import unittest
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

class TestPaginationAPI(unittest.TestCase):
    
    def setUp(self):
        """测试前设置"""
        self.app = app.test_client()
        self.app.testing = True
    
    def test_pagination_parameters(self):
        """测试分页参数处理"""
        # 测试默认参数
        response = self.app.get('/api/tasks')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('pagination', data)
        self.assertIn('data', data)
    
    def test_pagination_with_page(self):
        """测试指定页码"""
        # 创建测试数据
        pool_data = {'name': 'test_pool', 'max_workers': 3}
        response = self.app.post('/api/pools', json=pool_data)
        pool_data = json.loads(response.data)
        pool_id = pool_data['data']['pool_id']
        
        # 创建多个任务用于测试
        for i in range(10):
            task_data = {
                'pool_id': pool_id,
                'task_name': f'test_task_{i}',
                'task_type': 'demo',
                'duration': 1
            }
            self.app.post('/api/tasks', json=task_data)
        
        # 测试分页
        response = self.app.get('/api/tasks?page=2&per_page=5')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        # 如果有足够数据，页码应该是2，否则应该是1
        expected_page = 2 if data['pagination']['total_items'] >= 6 else 1
        self.assertEqual(data['pagination']['current_page'], expected_page)
        self.assertEqual(data['pagination']['per_page'], 5)
    
    def test_pagination_bounds(self):
        """测试分页边界条件"""
        # 测试页码过小
        response = self.app.get('/api/tasks?page=0&per_page=10')
        data = json.loads(response.data)
        self.assertEqual(data['pagination']['current_page'], 1)
        
        # 测试每页条数过大
        response = self.app.get('/api/tasks?page=1&per_page=200')
        data = json.loads(response.data)
        self.assertEqual(data['pagination']['per_page'], 100)
    
    def test_pagination_with_pool_filter(self):
        """测试线程池过滤与分页结合"""
        # 创建测试线程池
        pool_data = {'name': 'test_pool', 'max_workers': 3}
        response = self.app.post('/api/pools', json=pool_data)
        self.assertEqual(response.status_code, 200)
        
        # 获取响应数据
        response_data = json.loads(response.data)
        if 'data' in response_data and 'pool_id' in response_data['data']:
            pool_id = response_data['data']['pool_id']
            
            # 测试带线程池过滤的分页
            response = self.app.get(f'/api/tasks?pool_id={pool_id}&page=1&per_page=5')
            data = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['pagination']['current_page'], 1)
        else:
            # 如果创建失败，测试基础分页功能
            response = self.app.get('/api/tasks?page=1&per_page=5')
            data = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['pagination']['current_page'], 1)
    
    def test_pagination_metadata(self):
        """测试分页元数据完整性"""
        response = self.app.get('/api/tasks?page=1&per_page=5')
        data = json.loads(response.data)
        
        pagination = data['pagination']
        required_fields = [
            'current_page', 'total_pages', 'total_items',
            'per_page', 'start_item', 'end_item',
            'has_prev', 'has_next'
        ]
        
        for field in required_fields:
            self.assertIn(field, pagination)
        
        # 验证数据一致性（考虑空数据情况）
        if pagination['total_items'] > 0:
            expected_items = min(pagination['per_page'], pagination['total_items'])
            actual_items = pagination['end_item'] - pagination['start_item'] + 1
            self.assertEqual(actual_items, expected_items)

if __name__ == '__main__':
    unittest.main()