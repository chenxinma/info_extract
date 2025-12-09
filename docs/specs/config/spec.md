# 配置模块详细设计

## 目的
定义信息抽取项目配置模块的数据模型和数据库接口，提供配置数据的访问和管理功能。

## 数据库定义

```sql
-- example definition
CREATE TABLE example (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	fragment TEXT
);

-- info_item definition
CREATE TABLE info_item (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	label TEXT NOT NULL,
	"describe" TEXT,
	data_type TEXT,
	sort_no INTEGER,
	sample_col_name TEXT
);

-- extraction definition
CREATE TABLE extraction (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	example_id INTEGER,
	extraction_info_item_id INTEGER,
	extraction_text TEXT,
	CONSTRAINT extraction_example_FK FOREIGN KEY (example_id) REFERENCES example(id),
	CONSTRAINT extraction_info_item_FK FOREIGN KEY (extraction_info_item_id) REFERENCES info_item(id)
);

-- ext_attribute definition
CREATE TABLE ext_attribute (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	extraction_id INTEGER,
	"key" TEXT NOT NULL,
	value TEXT NOT NULL,
	CONSTRAINT ext_attribute_extraction_FK FOREIGN KEY (extraction_id) REFERENCES extraction(id)
);

-- mapping_cache definition
CREATE TABLE mapping_cache (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	hash_key TEXT NOT NULL UNIQUE,
	sql_code TEXT NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 需求
### 需求：配置数据模型
系统需要定义配置数据的结构模型，包括信息项和示例数据。

#### 场景：信息项模型
- 当系统需要获取待抽取的信息项时
- 系统将返回包含以下属性的 InfoItem 对象：
  - id: 信息项的唯一标识符
  - label: 信息项的标签名称
  - describe: 信息项的描述（可选）
  - data_type: 信息项的数据类型
  - sort_no: 排序号，用于控制显示顺序
  - sample_col_name: 示例列名，用于SQL映射

#### 场景：示例模型
- 当系统需要获取抽取示例时
- 系统将返回包含以下属性的 Example 对象：
  - id: 示例的唯一标识符
  - fragment: 示例文本片段

### 需求：配置数据库接口
系统需要提供对配置数据库（standard.db）的访问接口。

#### 场景：获取信息项
- 当系统需要获取所有信息项时
- 系统将查询 info_item 表并按 sort_no 排序返回 InfoItem 对象列表

#### 场景：获取示例数据
- 当系统需要获取所有示例时
- 系统将查询 example 表返回 Example 对象列表

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
系统需要提供配置相关的实用函数。

#### 场景：生成输出列定义
- 当系统需要获取Excel输出的标准表头定义时
- 系统将从./config目录下的 standard.db 读取 info_item 表，按sort_no升序
- 输出 list[ColumnDefine]
    ```python
    class ColumnDefine(TypedDict):
        name: str
        dtype: str
        describe: str
    ```

#### 场景：生成信息项定义提示词
- 当系统需要生成抽取提示词时
- 系统将连接从./config目录下的 standard.db 读取 info_item 表，按sort_no升序
- 逐一拼接信息并输出str

#### 场景：获取示例数据
- 当系统需要获取示例数据用于训练或测试时
- 系统将连接从./config目录下的 standard.db
- 读取 example 表
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
- 系统将从standard.db读取info_item表
- 按照sample_col_name和label生成SELECT语句样例

#### 场景：管理缓存SQL
- 当系统需要缓存或获取已缓存的SQL映射结果时
- 系统将提供 get_cached_mapping_sql 和 save_mapping_sql 接口
- get_cached_mapping_sql 通过 hash_key 从 mapping_cache 表获取SQL代码
- save_mapping_sql 通过 hash_key 将SQL代码保存到 mapping_cache 表
- 确保相同表头结构的SQL映射结果可以被复用