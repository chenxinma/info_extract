## 开发环境

项目使用 uv 做python依赖管理
- 添加依赖包 `uv add {依赖包}`
- 程序运行 `uv run {程序入口}`
- 单元测试 `uv run -m unittest ./tests/xxx.py`

### 目录说明

config: 参数、提示词等配置信息
docs: 设计文档
src: python程序源码
tests: unittests
web: flask 界面html模板
log: 日志

## 程序示例

1. msg文件格式邮件，读取邮件文件正文
** msg-parser usage **
```python
from msg_parser import MsOxMessage

msg_obj = MsOxMessage(msg_file_path)
json_string = msg_obj.get_message_as_json()
msg_properties_dict = msg_obj.get_properties()
saved_path = msg_obj.save_email_file(output_eml_file_path)
```

## 设计文档

### 设计文档目录结构

docs/                         # 设计文档位置
├── specs/
│   ├── source/
│   │   └── spec.md           # Current source load spec (if exists)
│   ├── extract/
│   │   └── spec.md           # Current extract structure data spec (if exists)
│   └── destination/
│       └── spec.md           # Current export to destination spec (if exists)
└── changes/
    └── add-pdf_source/       # 新增功能的文档位置
        ├── proposal.md       # Why and what changes
        ├── tasks.md          # Implementation checklist
        ├── design.md         # Technical decisions (optional)
        └── specs/
            └── pdf/
                └── spec.md   # Delta showing additions

### spec.md样例模板

```markdown
# 认证详细设计

## 目的
认证和会话管理。

## 需求
### 需求：用户认证
系统应在成功登录时颁发JWT令牌。

#### 场景：有效凭据
- 当用户提交有效凭据时
- 系统将返回JWT令牌
...
```

### 增量、修改设计的样例模板

```markdown
# 认证变更

## 新增需求
### 需求：双因素认证
系统必须在登录过程中要求第二个验证因素。

#### 场景：需要OTP验证码
- 当用户提交有效凭据时
- 系统将要求进行OTP验证码验证
```
