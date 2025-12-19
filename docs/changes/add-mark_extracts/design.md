# 划词信息项标记技术设计

## 架构概览
划词信息项标记功能分为前端界面和后端服务两部分。前端负责用户交互和数据展示，后端提供数据存储和API接口。

## 数据模型设计

config_models.py 定义了数据模型 Example、InfoItem

### 示例文本 (Example, 既有表 example)  
存储用于标注的文本片段：
- id: 主键，整数类型，自动递增
- fragment: 文本片段内容，字符串类型，非空
- profile_id: 配置分组
- created_at: 创建时间戳，时间类型，默认为当前时间
- updated_at: 更新时间戳，时间类型，默认为当前时间

### 标注记录 (既有表 extraction) 对象 langextract.data.Extraction
存储对文本片段的标注信息：
- id: 主键，整数类型，自动递增
- example_id: 外键，关联示例文本表，整数类型，非空
- extraction_info_item_id:  外键，信息项info_itme表，整数类型，非空
- extraction_text: 标注的文本内容，字符串类型，非空
- created_at: 创建时间戳，时间类型，默认为当前时间
- updated_at: 更新时间戳，时间类型，默认为当前时间

### 标注属性 (既有表 ext_attribute) 对象 dict[str, str]
存储标注记录的附加属性：
- id: 主键，整数类型，自动递增
- extraction_id: 外键，关联标注记录extraction表，整数类型，非空
- "key": 属性键名，字符串类型，非空
- value: 属性值，字符串类型，非空
- created_at: 创建时间戳，时间类型，默认为当前时间
- updated_at: 更新时间戳，时间类型，默认为当前时间

## API接口设计

### 示例文本管理接口

#### GET /api/example
获取所有示例文本列表
- 请求参数：无
- 返回：示例文本对象数组

#### POST /api/example
创建新的示例文本
- 请求体：JSON对象，包含fragment字段
- 返回：新创建的示例文本对象

#### PUT /api/example/{id}
更新指定ID的示例文本
- 路径参数：id - 示例文本ID
- 请求体：JSON对象，包含fragment字段
- 返回：更新后的示例文本对象

#### DELETE /api/example/{id}
删除指定ID的示例文本
- 路径参数：id - 示例文本ID
- 返回：无内容

#### GET /api/example/{id}/extractions
获取指定示例文本的所有标注记录
- 路径参数：id - 示例文本ID
- 返回：标注记录对象数组

### 标注记录管理接口

#### GET /api/extractions
获取所有标注记录（可选分页和过滤）
- 请求参数：page, limit, example_text_id（可选）
- 返回：标注记录对象数组

#### POST /api/extractions
创建新的标注记录
- 请求体：JSON对象，包含example_text_id, text, info_item_type, position_start, position_end字段
- 返回：新创建的标注记录对象

#### PUT /api/extractions/{id}
更新指定ID的标注记录
- 路径参数：id - 标注记录ID
- 请求体：JSON对象，包含text, info_item_type, position_start, position_end字段
- 返回：更新后的标注记录对象

#### DELETE /api/extractions/{id}
删除指定ID的标注记录
- 路径参数：id - 标注记录ID
- 返回：无内容

### 标注属性管理接口

#### GET /api/extractions/{extraction_id}/attributes
获取指定标注记录的所有属性
- 路径参数：extraction_id - 标注记录ID
- 返回：标注属性对象数组

#### POST /api/extractions/{extraction_id}/attributes
为指定标注记录添加属性
- 路径参数：extraction_id - 标注记录ID
- 请求体：JSON对象，包含key, value字段
- 返回：新创建的标注属性对象

#### PUT /api/extractions/{extraction_id}/attributes/{id}
更新指定ID的标注属性
- 路径参数：extraction_id - 标注记录ID, id - 属性ID
- 请求体：JSON对象，包含key, value字段
- 返回：更新后的标注属性对象

#### DELETE /api/extractions/{extraction_id}/attributes/{id}
删除指定ID的标注属性
- 路径参数：extraction_id - 标注记录ID, id - 属性ID
- 返回：无内容

## 前端实现细节

### 前端界面设计
docs/ui/mark_extracts.html

### 前端界面开发
src/info_extract/web/mark_extracts.html

### 划词标注实现
采用contenteditable div元素实现文本编辑功能，通过JavaScript监听鼠标事件捕获用户选择的文本：
1. 使用window.getSelection()获取用户选中的文本范围
2. 将选中文本替换为带有特殊标识的span标签
3. 在内部维护一个映射表记录占位符与实际文本、类型的对应关系

### 界面状态管理
在前端维护以下状态变量：
- examples: 所有示例文本的数组
- currentExampleId: 当前正在编辑的示例ID
- extractions: 当前示例的所有标注记录
- selectedExtraction: 当前选中的标注记录
- placeholderMap: 占位符与信息的映射

### 与后端交互策略
前端定期将更改同步到后端，或在用户执行保存操作时触发同步。对于频繁的操作（如标注），可采用缓存+批量提交的方式减少网络请求。

## 性能考虑
1. 对于大量示例文本的展示，采用虚拟滚动或分页加载
2. 数据库查询需添加适当索引以提升检索效率
3. 实现合理的缓存策略以减少重复的数据获取