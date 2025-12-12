# 配置模块详细设计

## 目的
定义信息抽取项目配置模块的数据模型和数据库接口，提供配置数据的访问和管理功能。同时实现Profile配置机制，支持在单一应用程序中管理多套配置集合，允许用户快速切换配置。

## 数据库定义

```sql
-- profile definition
CREATE TABLE profile (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_default BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- example definition
CREATE TABLE example (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	fragment TEXT,
	profile_id INTEGER NOT NULL DEFAULT 1,
	CONSTRAINT fk_example_profile
        FOREIGN KEY (profile_id) REFERENCES profile(id)
);

-- info_item definition
CREATE TABLE info_item (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	label TEXT NOT NULL,
	"describe" TEXT,
	data_type TEXT,
	sort_no INTEGER,
	sample_col_name TEXT,
	profile_id INTEGER NOT NULL DEFAULT 1,
	CONSTRAINT fk_info_item_profile
        FOREIGN KEY (profile_id) REFERENCES profile(id)
);

-- extraction definition
CREATE TABLE extraction (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	example_id INTEGER,
	extraction_info_item_id INTEGER,
	extraction_text TEXT,
	profile_id INTEGER NOT NULL DEFAULT 1,
	CONSTRAINT extraction_example_FK FOREIGN KEY (example_id) REFERENCES example(id),
	CONSTRAINT extraction_info_item_FK FOREIGN KEY (extraction_info_item_id) REFERENCES info_item(id),
	CONSTRAINT fk_extraction_profile
        FOREIGN KEY (profile_id) REFERENCES profile(id)
);

-- ext_attribute definition
CREATE TABLE ext_attribute (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	extraction_id INTEGER,
	"key" TEXT NOT NULL,
	value TEXT NOT NULL,
	profile_id INTEGER NOT NULL DEFAULT 1,
	CONSTRAINT ext_attribute_extraction_FK FOREIGN KEY (extraction_id) REFERENCES extraction(id),
	CONSTRAINT fk_ext_attribute_profile
        FOREIGN KEY (profile_id) REFERENCES profile(id)
);

-- mapping_cache definition
CREATE TABLE mapping_cache (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	hash_key TEXT NOT NULL UNIQUE,
	sql_code TEXT NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- profile_metadata definition (optional metadata table)
CREATE TABLE profile_metadata (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    CONSTRAINT fk_profile_metadata_profile
        FOREIGN KEY (profile_id) REFERENCES profile(id)
);
```

## 需求

### 需求：Profile配置支持
系统需要支持通过Profile来管理多套配置信息。

#### 场景：Profile数据结构
- 当用户启动系统并指定Profile时
- 系统将从`standard.db`数据库中根据profile_id过滤配置数据
- 如果未指定Profile，则使用默认的`default` profile的数据

#### 场景：Profile配置定义
- 系统支持在`standard.db`数据库中定义多个Profile
- 每个Profile通过数据库记录进行区分
- 每个Profile在数据库中存储：
  - profile表记录Profile的基本信息
  - info_item、example、extraction等表通过外键引用profile_id
  - profile_metadata表记录Profile的元信息（可选）
    - name: Profile的显示名称
    - description: Profile的描述信息
    - version: Profile的版本信息

#### 场景：Profile切换
- 系统提供API接口`GET /api/config/profiles`获取可用的Profiles列表
- 系统提供API接口`POST /api/config/profiles/switch`切换到指定的Profile
- 切换后，所有配置相关的功能将使用新Profile的数据
- 切换操作应更新内部状态并在内存中重新加载配置

### 需求：向后兼容性
系统需要保持与现有配置的兼容性。

#### 场景：默认Profile模式
- 当系统启动且没有指定Profile时
- 系统将使用默认的`default` profile的数据
- 所有现有功能继续正常工作

### 需求：Profile配置管理
系统需要提供Profile的管理功能。

#### 场景：获取可用Profile列表
- 当客户端请求获取Profile列表时
- 系统将查询`profile`表
- 返回包含所有可访问的Profile信息的对象列表：
  - id: Profile的唯一标识符（数据库中的ID）
  - name: Profile的显示名称
  - description: Profile的描述信息
  - isActive: 是否为当前激活的Profile

#### 场景：创建新Profile
- 当管理员需要创建新Profile时
- 系统将在`profile`表中创建新记录
- 可以复制现有Profile的配置数据到新Profile

### 需求：配置数据模型
系统需要定义配置数据的结构模型，包括信息项和示例数据，并与Profile关联。

#### 场景：信息项模型
- 当系统需要获取待抽取的信息项时
- 系统将返回包含以下属性的 InfoItem 对象：
  - id: 信息项的唯一标识符
  - label: 信息项的标签名称
  - describe: 信息项的描述（可选）
  - data_type: 信息项的数据类型
  - sort_no: 排序号，用于控制显示顺序
  - sample_col_name: 示例列名，用于SQL映射
  - profile_id: 所属的Profile ID，用于区分不同配置集合

#### 场景：示例模型
- 当系统需要获取抽取示例时
- 系统将返回包含以下属性的 Example 对象：
  - id: 示例的唯一标识符
  - fragment: 示例文本片段
  - profile_id: 所属的Profile ID，用于区分不同配置集合

### 需求：配置数据库接口
系统需要提供对配置数据库（standard.db）的访问接口，支持Profile过滤。

#### 场景：获取信息项
- 当系统需要获取所有信息项时
- 系统将查询 info_item 表并按 sort_no 排序，根据当前Profile过滤返回 InfoItem 对象列表

#### 场景：获取示例数据
- 当系统需要获取所有示例时
- 系统将查询 example 表，根据当前Profile过滤返回 Example 对象列表

#### 场景：获取提取物
- 当系统需要获取特定示例的提取物时
- 系统将查询 extraction 表和 info_item 表的关联数据
- 通过 example_id 获取相关提取物数据
- 系统将返回 Extraction 对象列表

#### 场景：获取提取物属性
- 当系统需要获取特定提取物的属性时
- 系统将通过 extraction_id 查询 ext_attribute 表返回键值对字典

#### 场景：缓存映射SQL
- 当系统需要缓存SQL映射结果时
- 系统将使用哈希键作为唯一标识存储SQL代码到 mapping_cache 表
- 当需要获取已缓存的SQL时，系统将通过哈希键从 mapping_cache 表查询

### 需求：配置工具函数
系统需要提供配置相关的实用函数，支持基于Profile的配置访问。

#### 场景：生成输出列定义
- 当系统需要获取Excel输出的标准表头定义时
- 系统将从./config目录下的 standard.db 读取 info_item 表，按sort_no升序，根据当前Profile过滤
- 输出 list[ColumnDefine]
    ```python
    class ColumnDefine(TypedDict):
        name: str
        dtype: str
        describe: str
    ```

#### 场景：生成信息项定义提示词
- 当系统需要生成抽取提示词时
- 系统将连接从./config目录下的 standard.db 读取 info_item 表，按sort_no升序，根据当前Profile过滤
- 逐一拼接信息并输出str

#### 场景：获取示例数据
- 当系统需要获取示例数据用于训练或测试时
- 系统将连接从./config目录下的 standard.db
- 读取 example 表，根据当前Profile过滤
    - 逐行创建 langextract.data.ExampleData 对象 将example.fragment 填入 ExampleData的 text
    - 按 example.id 从extraction表获得所有相关的extraction.example_id = example.id的数据
        ```sql
        -- extraction 取数
        SELECT
            ii.label,
            e.extraction_text,
        from
            extraction e
        inner join info_item ii
        on
            e.extraction_info_item_id = ii.id
        where
            e.example_id = ?
        ```
        - 逐行创建langextract.data.Extraction 对象 extraction_class = extraction.label, extraction_text = extraction.extraction_text
            - 按 extraction.id 获得 ext_attribute，如果有数据则以dict[str, str] 填入 langextract.data.Extraction 对象的attributes
                ```sql
                SELECT
                    ea."key",
                    ea.value
                from
                    ext_attribute ea
                where
                    e.extraction_id = ?
                ```
        - 把获得的所有 langextract.data.Extraction 对象 填入 langextract.data.ExampleData 对象的 extractions

#### 场景：生成示例SQL
- 当系统需要生成SQL映射示例时
- 系统将从standard.db读取info_item表，根据当前Profile过滤
- 按照sample_col_name和label生成SELECT语句样例

#### 场景：管理缓存SQL
- 当系统需要缓存或获取已缓存的SQL映射结果时
- 系统将提供 get_cached_mapping_sql 和 save_mapping_sql 接口
- get_cached_mapping_sql 通过 hash_key 从 mapping_cache 表获取SQL代码
- save_mapping_sql 通过 hash_key 将SQL代码保存到 mapping_cache 表
- 确保相同表头结构的SQL映射结果可以被复用

## 架构变更

### ConfigManager类
创建新的配置管理器类来处理Profile逻辑：

```python
class ConfigManager:
    def __init__(self, default_profile: str = "default"):
        self.current_profile_id = self._get_profile_id(default_profile)
        self.config_db = ConfigDB(active_profile_id=self.current_profile_id)

    def get_available_profiles(self) -> List[ProfileInfo]:
        # 获取所有可用Profile列表

    def switch_profile(self, profile_id: int) -> bool:
        # 切换到指定Profile

    def get_current_profile(self) -> str:
        # 获取当前Profile ID

    def _get_profile_id(self, profile_name: str) -> int:
        # 根据Profile名称获取ID

    def reload_config(self):
        # 重新加载配置
```

### ConfigDB类变更
更新ConfigDB类以支持基于Profile的查询：

```python
class ConfigDB:
    def __init__(self, db_path: str | Path = None, active_profile_id: int = 1):
        # 支持指定活动的Profile ID
        # 所有数据库查询将基于active_profile_id进行过滤
        self.active_profile_id = active_profile_id
```

### 工具函数变更
所有配置相关的工具函数需要修改以使用全局ConfigManager实例：

```python
# 全局配置管理器实例
config_manager: ConfigManager

def output_info_items() -> list[ColumnDefine]:
    # 使用当前激活的Profile的配置
    config_db = config_manager.config_db
    # ... 其余逻辑
```

## API接口规范

### 获取可用Profiles
- 端点：`GET /api/config/profiles`
- 响应：`List[ProfileInfo]`
- 示例响应：
```json
[
  {
    "id": 1,
    "name": "Default Profile",
    "description": "Default configuration",
    "isActive": true
  },
  {
    "id": 2,
    "name": "Financial Reports",
    "description": "Configuration for financial document processing",
    "isActive": false
  }
]
```

### 切换Profile
- 端点：`POST /api/config/profiles/switch`
- 请求体：`{"profile_id": integer}`
- 响应：`{"success": boolean, "message": string}`
- 示例请求：
```json
{
  "profile_id": 2
}
```
- 示例响应：
```json
{
  "success": true,
  "message": "Profile switched successfully"
}
```

### 获取当前Profile
- 端点：`GET /api/config/profiles/current`
- 响应：`ProfileInfo`
- 示例响应：
```json
{
  "id": 2,
  "name": "Financial Reports",
  "description": "Configuration for financial document processing",
  "isActive": true
}
```

## UI界面规范

### Profile切换界面
- 在顶部导航栏添加Profile选择下拉框
- 下拉框显示当前激活的Profile名称
- 点击下拉框展开所有可用的Profile列表
- 当前激活的Profile在列表中用特殊图标和标记标识

#### 界面元素
- 下拉按钮：显示当前激活的Profile名称，带用户图标前缀
- Profile列表：每个Profile项包含：
  - 状态图标：激活的Profile显示勾选图标，其他显示用户图标
  - Profile名称：显示Profile的名称
  - 状态标记：激活的Profile显示"当前"标签

#### 交互行为
- 页面加载时自动获取并显示当前激活的Profile
- 用户点击Profile项时触发切换操作
- 切换成功后显示提示信息并可选择是否刷新页面
- 切换后更新下拉按钮显示的Profile名称

## 部署和配置说明

### 数据库结构说明
```
config/
└── standard.db                 # 单一数据库，包含所有profiles的配置
    ├── profile                 # Profile基本信息表
    ├── info_item             # 信息项定义，带profile_id外键
    ├── example               # 示例数据，带profile_id外键
    ├── extraction            # 提取规则，带profile_id外键
    └── ext_attribute         # 提取属性，带profile_id外键
```

## 迁移指南

### 现有配置迁移
对于现有的单数据库配置，系统将提供迁移脚本自动执行以下操作：

1. 在`standard.db`中创建`profile`表并添加默认profile记录
2. 为现有表（info_item、example、extraction、ext_attribute）添加`profile_id`列
3. 为所有现有记录设置默认的`profile_id=1`
4. 建立外键约束关系
5. 可选：在`profile_metadata`表中添加配置版本信息

### 版本兼容性
- 新版本完全向后兼容旧版本的单一数据库配置（通过迁移脚本）
- 新的Profile功能是可选的增强功能
- 现有的API调用在迁移后将继续正常工作
- 所有配置相关的功能将默认使用`default`profile的数据