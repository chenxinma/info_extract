# 任务中断功能详细设计

## 目的
实现对正在运行的文件处理任务的中断功能，允许用户在任务执行过程中取消操作。

## 需求
### 需求：任务中断
系统应允许用户中断正在运行的文件处理任务。

#### 场景：用户触发中断
- 当用户点击任务列表中的"取消"按钮时
- 系统应立即停止当前任务的执行
- 任务状态应更新为"已取消"
- 相关资源应被释放

## 技术实现

### 后端实现

#### 1. Pipeline类
修改Pipeline类以支持中断机制：

```python
# 在Pipeline类中添加
self.cancellation_event = threading.Event()

# 修改run方法
async def run(self, cancellation_event=None) -> AsyncGenerator[str, None]:
    # 在每个处理步骤中检查中断事件
    if cancellation_event and cancellation_event.is_set():
        return  # 中断执行
```

#### 2. UI模块
更新UI模块中的任务管理：

```python
# 在UI类中添加
self.running_executors: Dict[str, Tuple[Executor, threading.Event]] = {}

# 取消任务时触发中断
@app.post('/api/tasks/{task_id}/cancel')
async def cancel_task(task_id: str):
    # 设置中断事件
    if task_id in self.running_executors:
        cancellation_event = self.running_executors[task_id][1]
        cancellation_event.set()
```

### 前端实现

#### 任务UI
- 在任务项中添加"取消"按钮
- 点击按钮时调用取消API
- 实时更新任务状态

## 流程图
```
用户点击取消按钮
    ↓
前端发送取消请求到 /api/tasks/{taskId}/cancel
    ↓
后端设置中断事件标志
    ↓
Pipeline检查到中断事件，停止执行
    ↓
更新任务状态为"已取消"
```