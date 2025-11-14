# 标准配置系统文档

## 概述

新的标准配置系统将所有配置信息集中存储在 `config/standard.db` SQLite数据库中，替代了原来分散在多个文件中的配置方式。

## 数据库结构

数据库包含以下四个表：

1. `info_item` - 存储需要抽取的信息项定义
2. `example` - 存储用于训练AI的示例文本
3. `extraction` - 存储示例文本中信息项的提取映射
4. `ext_attribute` - 存储提取项的额外属性

## 使用方法

### 1. 读取配置信息

```python
from src.info_extract.config import ConfigDB

# Initialize the configuration database
config_db = ConfigDB()

# Get all information items
info_items = config_db.get_info_items()

# Get a specific information item by label
name_item = config_db.get_info_item_by_label("姓名")

# Get all examples
examples = config_db.get_examples()
```

### 2. 生成配置文件

系统可以基于数据库内容生成不同格式的配置文件：

```python
from src.info_extract.config.config_utils import (
    write_email_yaml, 
    write_output_yaml, 
    generate_spreadsheet_configs
)

# Generate email.yaml from database
write_email_yaml()

# Generate output.yaml from database
write_output_yaml()

# Generate spreadsheet configuration files
generate_spreadsheet_configs()
```

## 优势

1. **统一存储** - 所有配置信息集中在一个数据库中
2. **易于维护** - 修改配置只需要在数据库中操作
3. **数据一致性** - 避免了不同配置文件间的不一致
4. **可扩展性** - 容易添加新的配置项和示例