# 提案：配置信息从数据库获取

## 问题陈述
目前的配置从文本信息的结构化提取、excel文件的列映射、标准excel表头定义，分散在./config目录的 email.yaml、spreadsheet_00000.txt、output.yaml 三个文件中。需要多处维护。

## 提出的解决方案
将配置归口到./config下standard.db 的sqlite数据库中。

## 优势
统一定义信息项，去除重复定义。

## 实现方法
读取sqlite数据库，提供各个模块所需配置信息。
- 代替 output.yaml，读取info_item表，按sort_no升序
    - 输出 list[ColumnDefine]
        ```python
        class ColumnDefine(TypedDict):
            name: str
            type: str
        ```
- 代替 spreadsheet_00000.txt，读取info_item表，按sort_no升序，输出str
- 代替 email.yaml，读取数据并生成一组 langextract.data.ExampleData
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


### 数据库定义

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
	sort_no INTEGER
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
```
