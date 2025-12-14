# 任务中断功能技术设计

## 概述
当前系统允许用户启动文件处理任务，但缺少中断长时间运行任务的能力。本设计实现一个完整的任务中断机制。

## 技术架构

### 1. Pipeline中断机制
- 在`Pipeline`类中添加`cancellation_event`属性
- 使用`threading.Event`作为中断令牌
- 在管道执行的关键点检查中断事件

### 2. UI模块任务管理
- 添加`running_executors`字典跟踪运行中的执行器
- 在执行器中传递中断事件
- 更新取消端点以触发中断

### 3. 执行流程
- 启动任务时创建`threading.Event`
- 将事件与任务ID关联
- 在执行过程中定期检查中断信号
- 收到取消请求时设置中断事件

## 代码结构变更

### Pipeline类变更
- 添加`cancellation_event`属性
- 修改`run`方法以接受和检查中断事件

### UI类变更
- 添加`running_executors`属性
- 更新`create_task_stream`方法
- 更新`cancel_task`方法

### 前端变更
- 更新任务UI以显示取消按钮
- 实现取消按钮事件处理