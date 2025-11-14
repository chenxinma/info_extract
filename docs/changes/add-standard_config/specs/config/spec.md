# 信息项配置管理

## 目的
读写./config目录下的 standard.db，sqlite的数据文件。获得标准信息项和用于文本结构话提取的example配置。


## 需求

### 需求：提供excel输出的标准表头定义
提供一个公共方法，可以按sort_no升序提供表头定义。

#### 场景：提供excel输出的标准表头定义
- 从./config目录下的 standard.db 读取 info_item 表，按sort_no升序
- 输出 list[ColumnDefine]
    ```python
    class ColumnDefine(TypedDict):
        name: str
        type: str
    ```

### 需求：提供取数映射提示词
提供一个公共方法，可以按sort_no升序提供取数映射提示词。

#### 场景：提供取数映射提示词
- 连接 从./config目录下的 standard.db 读取 info_item 表，按sort_no升序
- 逐一拼接信息并输出str

### 需求：提供取数映射提示词
从standard.db读取数据并生成一组 langextract.data.ExampleData

#### 场景：提供取数映射提示词
- 连接 从./config目录下的 standard.db
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

 