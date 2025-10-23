## 开发环境
项目使用 uv 做python依赖管理
- 添加依赖包 `uv add {依赖包}`
- 程序运行 `uv run {程序入口}`

## 程序实现
1. 读取邮件文件正文
** msg-parser usage **
```python
from msg_parser import MsOxMessage

msg_obj = MsOxMessage(msg_file_path)
json_string = msg_obj.get_message_as_json()
msg_properties_dict = msg_obj.get_properties()
saved_path = msg_obj.save_email_file(output_eml_file_path)
```