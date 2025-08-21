# 线程池管理器

一个功能强大的Python线程池管理系统，提供线程池和任务的统一管理，包含Web管理界面。

[项目地址](https://github.com/854771076/python_threadpool_manager)

## 功能特性

- 🎯 **线程池管理**：创建、关闭、强制关闭线程池
- 📊 **任务管理**：提交、取消、监控任务执行状态
- 🔄 **动态调整**：运行时调整线程池大小，无需重启
- 🌐 **Web界面**：基于Bootstrap的响应式管理界面
- 📈 **实时监控**：实时查看线程池和任务状态
- 🔧 **配置灵活**：支持自定义配置和扩展
- 🧪 **完整测试**：包含全面的单元测试
- 🎛️ **智能建议**：基于负载自动推荐线程数

## 项目结构

```
线程池管理/
├── src/
│   └── threadpool_manager/
│       ├── __init__.py          # 包初始化
│       ├── manager.py           # 线程池管理器
│       ├── managed_pool.py      # 自定义线程池
│       ├── managed_task.py      # 任务包装器
│       ├── exceptions.py        # 异常定义
│       └── enums.py             # 枚举类型
├── tests/                       # 测试文件
├── templates/                   # HTML模板
├── static/                      # 静态文件
├── doc/                         # 项目文档
│   ├── plan/                    # 需求文档
│   ├── plan-design/             # 详细需求设计
│   ├── dev-design/              # 技术架构设计
│   └── dev-progress/            # 开发进度
├── app.py                       # Flask应用主文件
├── requirements.txt             # 依赖文件
├── custom-conf.yml              # 配置文件
├── custom-conf-sample.yml       # 配置文件示例
└── README.md                    # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置项目

复制配置文件模板：

```bash
cp custom-conf-sample.yml custom-conf.yml
```

编辑 `custom-conf.yml` 根据需要修改配置。

### 3. 运行应用

```bash
python app.py
```

应用将在 http://127.0.0.1:5000 启动。

### 4. 使用Web界面

打开浏览器访问 http://127.0.0.1:5000，您可以看到：

- **线程池管理**：创建、查看、关闭线程池
- **任务管理**：提交、取消、监控任务
- **系统统计**：实时查看系统状态

## API使用

### 创建线程池

```python
from src.threadpool_manager import ThreadPoolManager

manager = ThreadPoolManager()
pool_id = manager.create_pool("my_pool", max_workers=5)
```

### 提交任务

```python
def my_task(x, y):
    return x + y

task_id = manager.submit_task(pool_id, my_task, "add_task", 1, 2)
```

### 管理任务

```python
# 获取任务信息
task = manager.get_task(task_id)
print(task.get_info())

# 取消任务
manager.cancel_task(task_id)

# 获取所有任务
tasks = manager.list_tasks()
```

### 关闭线程池

```python
# 优雅关闭
manager.close_pool(pool_id)

# 强制关闭
cancelled_tasks = manager.force_close_pool(pool_id)
```

## Web API

### 线程池管理

- `GET /api/pools` - 获取线程池列表
- `POST /api/pools` - 创建线程池
- `PUT /api/pools/<pool_id>/resize` - 调整线程池大小
- `GET /api/pools/<pool_id>/resize-info` - 获取调整信息
- `DELETE /api/pools/<pool_id>` - 关闭线程池
- `DELETE /api/pools/<pool_id>/force-close` - 强制关闭线程池

### 任务管理

- `GET /api/tasks` - 获取任务列表
- `POST /api/tasks` - 提交任务
- `GET /api/tasks/<task_id>` - 获取任务详情
- `DELETE /api/tasks/<task_id>` - 取消任务

### 系统信息

- `GET /api/stats` - 获取系统统计信息

## 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_manager.py
pytest tests/test_managed_pool.py

# 生成测试报告
pytest --cov=src --cov-report=html
```

## 配置说明

### 基本配置

```yaml
# Flask配置
flask:
  host: "127.0.0.1"
  port: 5000
  debug: true

# 线程池默认配置
thread_pool:
  default_max_workers: 5
  default_pool_name_prefix: "pool"

# 任务配置
task:
  default_task_name_prefix: "task"
  cleanup_interval_seconds: 300
  max_task_history: 1000
```

## 开发指南

### 添加新功能

1. 更新需求文档：`doc/plan-design/detailed-requirements.md`
2. 更新技术架构：`doc/dev-design/architecture.md`
3. 更新开发进度：`doc/dev-progress/progress.md`
4. 实现功能代码
5. 编写单元测试
6. 更新文档

### 扩展线程池类型

继承 `ManagedThreadPool` 类并实现自定义逻辑：

```python
class CustomThreadPool(ManagedThreadPool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 自定义初始化
  
    def custom_method(self):
        # 自定义方法
        pass
```

## 性能优化

- **线程安全**：使用线程锁保护共享数据
- **内存管理**：定期清理已完成的任务
- **状态缓存**：减少重复的状态查询
- **异步清理**：使用后台线程清理资源

## 故障排除

### 常见问题

1. **端口被占用**：修改 `custom-conf.yml` 中的端口号
2. **权限问题**：确保有读写日志文件的权限
3. **依赖冲突**：使用虚拟环境安装依赖

### 调试信息

设置日志级别为 DEBUG：

```yaml
logging:
  level: "DEBUG"
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0

- 初始版本发布
- 完整的线程池管理功能
- Web管理界面
- 全面的测试覆盖
