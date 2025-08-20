# 线程池管理项目技术架构设计

## 1. 系统架构概览

```mermaid
graph TB
    subgraph "前端界面"
        UI[管理界面<br/>Bootstrap+jQuery]
    end
    
    subgraph "后端服务"
        Flask[Flask Web服务]
        API[RESTful API]
        Manager[线程池管理器]
    end
    
    subgraph "核心组件"
        Pool[自定义线程池]
        Task[任务包装器]
        Monitor[状态监控器]
    end
    
    subgraph "数据存储"
        Memory[内存状态存储]
        Registry[线程池注册表]
    end
    
    UI -->|HTTP请求| Flask
    Flask --> API
    API --> Manager
    Manager --> Pool
    Manager --> Task
    Manager --> Monitor
    Pool --> Registry
    Task --> Memory
    Monitor --> Memory
```

## 2. 核心组件设计

### 2.1 线程池管理器（ThreadPoolManager）
```mermaid
classDiagram
    class ThreadPoolManager {
        -pools: Dict[str, ManagedThreadPool]
        -tasks: Dict[str, ManagedTask]
        +create_pool(name, max_workers): str
        +get_pool(pool_id): ManagedThreadPool
        +close_pool(pool_id): bool
        +list_pools(): List[PoolInfo]
        +submit_task(pool_id, task, task_name): str
        +cancel_task(task_id): bool
        +stop_task(task_id): bool
        +get_task(task_id): ManagedTask
        +list_tasks(): List[TaskInfo]
    }
```

### 2.2 自定义线程池（ManagedThreadPool）
```mermaid
classDiagram
    class ManagedThreadPool {
        -pool_id: str
        -name: str
        -executor: ThreadPoolExecutor
        -active_tasks: Dict[str, Future]
        +submit(task, task_name): str
        +shutdown(wait=True): void
        +shutdown_now(): List[Runnable]
        +get_status(): PoolStatus
        +get_active_tasks(): List[TaskInfo]
    }
```

### 2.3 任务包装器（ManagedTask）
```mermaid
classDiagram
    class ManagedTask {
        -task_id: str
        -name: str
        -future: Future
        -pool_id: str
        -submit_time: datetime
        -start_time: datetime
        -end_time: datetime
        -status: TaskStatus
        -result: Any
        -exception: Exception
        +cancel(): bool
        +stop(): bool
        +get_result(): Any
        +get_status(): TaskStatus
    }
```

## 3. 状态管理设计

### 3.1 线程池状态
```mermaid
stateDiagram-v2
    [*] --> RUNNING: 创建
    RUNNING --> SHUTDOWN: 优雅关闭
    RUNNING --> STOPPED: 强制关闭
    SHUTDOWN --> TERMINATED: 所有任务完成
    STOPPED --> [*]: 清理完成
    TERMINATED --> [*]: 清理完成
```

### 3.2 任务状态
```mermaid
stateDiagram-v2
    [*] --> PENDING: 提交任务
    PENDING --> RUNNING: 开始执行
    PENDING --> CANCELLED: 取消任务
    RUNNING --> COMPLETED: 正常完成
    RUNNING --> FAILED: 执行异常
    RUNNING --> CANCELLED: 停止任务
    COMPLETED --> [*]: 清理
    FAILED --> [*]: 清理
    CANCELLED --> [*]: 清理
```

## 4. 技术实现要点

### 4.1 线程安全
- 使用线程安全的字典存储线程池和任务
- 使用锁机制保护共享数据
- 使用原子操作更新状态

### 4.2 性能优化
- 使用弱引用避免内存泄漏
- 定期清理已完成的任务
- 使用缓存减少状态查询开销

### 4.3 异常处理
- 任务异常不会导致线程池崩溃
- 提供详细的异常信息和堆栈跟踪
- 支持任务重试机制

## 5. API设计

### 5.1 RESTful端点
```mermaid
sequenceDiagram
    participant Client
    participant Flask
    participant Manager
    
    Client->>Flask: POST /api/pools
    Flask->>Manager: create_pool()
    Manager-->>Flask: pool_id
    Flask-->>Client: 201 Created
    
    Client->>Flask: POST /api/tasks
    Flask->>Manager: submit_task()
    Manager-->>Flask: task_id
    Flask-->>Client: 202 Accepted
    
    Client->>Flask: GET /api/tasks/{id}
    Flask->>Manager: get_task()
    Manager-->>Flask: task_info
    Flask-->>Client: 200 OK
```

## 6. 扩展性设计

### 6.1 插件架构
- 支持自定义线程池实现
- 支持自定义任务包装器
- 支持自定义状态存储后端

### 6.2 配置管理
- 支持运行时配置修改
- 支持配置文件热加载
- 支持环境变量配置