# 任务取消功能详细设计

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

#### 实现细节：
- 通过API接口实现任务取消
- 使用`threading.Event`作为中断令牌
- 在管道执行的关键点检查中断事件
- 收到取消请求时设置中断事件
- 更新任务状态为cancelled并更新完成时间
- 真正中断正在运行的处理进程

## 技术实现

### 后端实现

#### 1. Executor类
修改Executor类以支持中断机制：
- 添加`cancellation_event`属性用于接收中断事件
- 修改`run`方法以接受和检查中断事件
- 在每个处理步骤中检查中断事件状态，若已设置则立即返回

##### 实现代码：
```python
# 在Executor.run方法中添加
async def run(self, profile_manager : ProfileManager, cancellation_event: Optional[threading.Event] = None) -> AsyncGenerator[str, None]:
    # 在每个处理步骤中检查中断事件
    if cancellation_event and cancellation_event.is_set():
        return  # 中断执行
```

#### 2. UI模块
更新UI模块中的任务管理：
- 添加`running_executors`属性跟踪运行中的执行器
- 启动任务时创建`threading.Event`并与任务ID关联
- 在执行过程中定期检查中断信号
- 收到取消请求时设置中断事件

##### 实现代码：
```python
# 在UI类中添加
self.running_executors: Dict[str, Tuple[Executor, threading.Event]] = {}

# 创建任务流时
cancellation_event = threading.Event()
self.running_executors[task_id] = (executor, cancellation_event)

async for txt in executor.run(profile_manager, cancellation_event=cancellation_event):
    # 检查中断事件
    if cancellation_event.is_set():
        # 停止执行并更新任务状态为已取消
        task_manager.update_status(task_id, "cancelled")
        break

# 取消任务时触发中断
@app.post('/api/tasks/{task_id}/cancel')
async def cancel_task(task_id: str):
    # 设置中断事件
    if task_id in self.running_executors:
        _, cancellation_event = self.running_executors[task_id]
        cancellation_event.set()
        
        # 从活动任务列表中移除
        del self.running_executors[task_id]
        
        return {"id": task_id, "status": "cancelled"}
```

### 前端实现

#### 任务UI
- 在任务项中添加"取消"按钮
- 点击按钮时调用取消API
- 实时更新任务状态

##### 实现细节：
- 任务状态包括：待处理、处理中、已完成、已失败、已取消
- 点击取消按钮时发送POST请求到 `/api/tasks/{taskId}/cancel`
- 接收到取消确认后，更新UI显示任务状态为"已取消"

## 流程图
```
用户点击取消按钮
    ↓
前端发送POST请求到 /api/tasks/{taskId}/cancel
    ↓
后端设置相应任务的中断事件标志
    ↓
Pipeline检查到中断事件，停止执行
    ↓
更新任务状态为"已取消"并通知前端
    ↓
前端UI更新显示任务状态
```

## 状态管理

### 任务状态变更
- 任务在"处理中"状态时显示"取消"按钮
- 用户点击"取消"按钮后，状态变为"取消中"
- 当后端确认任务已取消且资源已释放，状态变为"已取消"

### 资源管理
- 取消任务时及时释放与任务相关的资源
- 从`running_executors`字典中移除已取消的任务
- 确保线程安全地访问共享资源