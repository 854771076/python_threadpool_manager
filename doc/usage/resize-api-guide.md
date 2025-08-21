# 动态调整线程池大小API使用指南

## 概述

本指南详细介绍了如何使用动态调整线程池大小的API接口，包括Flask和Django两个版本的完整使用说明。

## API端点

### Flask版本

| 方法 | 端点                                 | 描述           |
| ---- | ------------------------------------ | -------------- |
| PUT  | `/api/pools/<pool_id>/resize`      | 调整线程池大小 |
| GET  | `/api/pools/<pool_id>/resize-info` | 获取调整信息   |

## 使用示例

### 1. 获取线程池调整信息

**请求示例**:

```bash
# Flask版本
curl -X GET http://localhost:5000/api/pools/pool-uuid-123/resize-info

# Django版本
curl -X GET http://localhost:8000/api/pools/pool-uuid-123/resize-info/
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "pool_id": "pool-uuid-123",
    "name": "default",
    "current_max_workers": 5,
    "active_tasks": 7,
    "can_resize": true,
    "status": "running",
    "suggested_max_workers": 9,
    "min_workers": 1,
    "max_workers": 50
  }
}
```

### 2. 调整线程池大小

**请求示例**:

```bash
# Flask版本
curl -X PUT http://localhost:5000/api/pools/pool-uuid-123/resize \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 10}'

# Django版本
curl -X PUT http://localhost:8000/api/pools/pool-uuid-123/resize/ \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 10}'
```

**成功响应**:

```json
{
  "success": true,
  "message": "线程池大小已成功从5调整到10",
  "data": {
    "pool_id": "pool-uuid-123",
    "old_max_workers": 5,
    "new_max_workers": 10,
    "migrated_tasks": 0,
    "active_tasks": 7,
    "status": "running"
  }
}
```

**错误响应**:

```json
{
  "success": false,
  "error": "线程池不存在"
}
```

## Python使用示例

### 使用requests库

```python
import requests

def resize_thread_pool(base_url, pool_id, new_size):
    """调整线程池大小"""
  
    # 1. 获取调整信息
    info_url = f"{base_url}/api/pools/{pool_id}/resize-info"
    response = requests.get(info_url)
  
    if response.status_code == 200:
        info = response.json()
        if info['success']:
            current_size = info['data']['current_max_workers']
            suggested_size = info['data']['suggested_max_workers']
            print(f"当前线程数: {current_size}, 建议: {suggested_size}")
  
    # 2. 执行调整
    resize_url = f"{base_url}/api/pools/{pool_id}/resize"
    data = {"max_workers": new_size}
    response = requests.put(resize_url, json=data)
  
    if response.status_code == 200:
        result = response.json()
        if result['success']:
            print(f"调整成功: {result['message']}")
            return True
        else:
            print(f"调整失败: {result['error']}")
    else:
        print(f"HTTP错误: {response.status_code}")
  
    return False

# 使用示例
if __name__ == "__main__":
    base_url = "http://localhost:5000"
    pool_id = "your-pool-id"
  
    # 调整到10个线程
    resize_thread_pool(base_url, pool_id, 10)
```

### 使用ThreadPoolManager直接调用

```python
from src.threadpool_manager import ThreadPoolManager

def direct_resize_example():
    """直接使用ThreadPoolManager调整"""
  
    manager = ThreadPoolManager()
  
    # 创建线程池
    pool_id = manager.create_pool("test_pool", max_workers=5)
  
    # 提交一些任务
    for i in range(3):
        manager.submit_task(pool_id, lambda x: x*2, f"task_{i}", i)
  
    # 获取调整信息
    info = manager.get_pool_resize_info(pool_id)
    print(f"当前: {info['current_max_workers']}, 建议: {info['suggested_max_workers']}")
  
    # 调整大小
    result = manager.resize_pool(pool_id, 8)
    if result['success']:
        print(f"调整成功: {result['message']}")
    else:
        print(f"调整失败: {result['error']}")

if __name__ == "__main__":
    direct_resize_example()
```

## 前端JavaScript使用示例

### 使用Fetch API

```javascript
// 获取调整信息
async function getResizeInfo(poolId) {
    try {
        const response = await fetch(`/api/pools/${poolId}/resize-info`);
        const data = await response.json();
    
        if (data.success) {
            return data.data;
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('获取调整信息失败:', error);
        throw error;
    }
}

// 调整线程池大小
async function resizePool(poolId, newSize) {
    try {
        const response = await fetch(`/api/pools/${poolId}/resize`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ max_workers: newSize })
        });
    
        const data = await response.json();
    
        if (data.success) {
            console.log('调整成功:', data.message);
            return data.data;
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('调整失败:', error);
        throw error;
    }
}

// 使用示例
async function exampleUsage() {
    const poolId = 'pool-uuid-123';
  
    try {
        // 获取当前信息
        const info = await getResizeInfo(poolId);
        console.log('当前信息:', info);
    
        // 调整到建议值
        const result = await resizePool(poolId, info.suggested_max_workers);
        console.log('调整结果:', result);
    
    } catch (error) {
        console.error('操作失败:', error);
    }
}
```

## 错误处理

### 常见错误及解决方案

| 错误类型     | HTTP状态码 | 解决方案                    |
| ------------ | ---------- | --------------------------- |
| 线程池不存在 | 404        | 检查pool_id是否正确         |
| 无效参数     | 400        | 确保max_workers在1-50范围内 |
| 线程池已关闭 | 400        | 重新创建线程池              |
| 系统错误     | 500        | 查看服务器日志              |

### 错误处理示例

```python
def handle_resize_errors():
    """错误处理示例"""
  
    try:
        response = requests.put(f"{base_url}/api/pools/{pool_id}/resize", 
                              json={"max_workers": new_size})
    
        if response.status_code == 404:
            print("线程池不存在，请检查pool_id")
        elif response.status_code == 400:
            error = response.json().get('error', '参数错误')
            print(f"参数错误: {error}")
        elif response.status_code == 500:
            print("服务器内部错误，请稍后重试")
        else:
            result = response.json()
            if result['success']:
                print("调整成功")
            else:
                print(f"调整失败: {result.get('error')}")
            
    except requests.exceptions.RequestException as e:
        print(f"网络错误: {e}")
```

## 最佳实践

### 1. 调整策略

```python
def smart_resize_strategy(pool_id, base_url):
    """智能调整策略"""
  
    # 获取当前信息
    info = requests.get(f"{base_url}/api/pools/{pool_id}/resize-info").json()
  
    if not info['success']:
        return False
  
    data = info['data']
    current = data['current_max_workers']
    active = data['active_tasks']
    suggested = data['suggested_max_workers']
  
    # 只有当建议值与当前值差异较大时才调整
    if abs(suggested - current) >= 2:
        return resize_thread_pool(base_url, pool_id, suggested)
  
    return False
```

### 2. 批量调整

```python
def batch_resize_pools(base_url, pool_configs):
    """批量调整多个线程池"""
  
    results = {}
  
    for pool_id, new_size in pool_configs.items():
        try:
            success = resize_thread_pool(base_url, pool_id, new_size)
            results[pool_id] = success
        except Exception as e:
            results[pool_id] = str(e)
  
    return results
```

## 监控和日志

### 1. 调整日志

每次调整操作都会记录详细日志：

- 调整时间
- 调整前后的线程数
- 迁移的任务数量
- 执行结果

### 2. 性能指标

- 调整耗时
- 任务迁移成功率
- 系统负载变化

## 测试脚本

### 快速测试

```bash
# Flask版本测试
python test_api.py

# Django版本测试
python test_django_api.py
```

### 手动测试

```bash
# 1. 获取系统统计
curl http://localhost:5000/api/stats

# 2. 获取线程池列表
curl http://localhost:5000/api/pools

# 3. 获取第一个线程池的调整信息
POOL_ID=$(curl -s http://localhost:5000/api/pools | jq -r '.data[0].pool_id')
curl http://localhost:5000/api/pools/$POOL_ID/resize-info

# 4. 调整线程池大小
curl -X PUT http://localhost:5000/api/pools/$POOL_ID/resize \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 8}'
```
