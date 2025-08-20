# 线程池管理项目需求

## 第一步：魔改线程池
- 魔改`from concurrent.futures import ThreadPoolExecutor`线程池
- 提交任务时记录任务的future
- 写一个线程池管理类，功能包括：
  - 创建或者管理已经存在的线程池
  - 管理所有线程池提交的任务future
  - 可取消提交的任务future
  - 可停止正在执行的任务future
  - 可关闭某线程池
  - 线程池和任务创建时，都需要添加名称，名称可自定义，默认使用uuid

## 第二步：管理界面
- 使用flask写一个管理界面
- 可查看和管理线程池管理类中的线程池和任务
- 前端使用bootstrap+jquery