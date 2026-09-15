# 估值表解析工具

`tools-vrp` 用于按 JSON 规则解析估值表，将持仓和产品指标输出为 JSON，或写入数据库。支持 Excel 97-2003、Excel 2007+ 和 CSV 文件。

## 环境要求

- Python 3.10 及以上
- [uv](https://docs.astral.sh/uv/)

在项目目录中安装依赖：

```bash
uv sync
```

如需连接 openGauss：

```bash
uv sync --extra gauss
```

## 快速使用

准备估值表和 `config.json` 后执行：

```bash
uv run vrp ./reports
```

参数可以是目录，也可以是单个文件：

```bash
uv run vrp ./reports/report.xlsx
```

程序处理目录时会读取其中所有 `.xls`、`.xlsx` 和 `.csv` 文件，并跳过 Excel 产生的 `~$` 临时文件。默认在原文件旁生成 `<文件名>.json`，内容分为 `positions` 和 `products` 两部分。

常用参数：

```text
-c, --config          指定解析配置，默认 config.json
--connection_url      指定 SQLAlchemy 数据库连接地址
--nofile              不生成 JSON 文件
--debug               输出调试日志
-v, --version         显示版本
```

配置文件会依次从估值表目录、当前目录和程序所在目录查找，也可以通过 `-c` 传入绝对路径。

## 配置示例

下面的配置从 A 列识别持仓行，读取一张持仓表和一张产品指标表：

```json
{
  "subject_code_column": "A",
  "env": {
    "BUSI_DATE": {
      "address": "B1",
      "type": "date"
    },
    "PRODUCT_CODE": {
      "address": "B2",
      "type": "str"
    }
  },
  "positions": [
    {
      "table": "POSITION_DETAIL",
      "default": {
        "BUSI_DATE": "$BUSI_DATE",
        "PRODUCT_CODE": "$PRODUCT_CODE"
      },
      "groups": [
        {
          "handlers": [
            {
              "subject_filter_regex": "^1103",
              "values": {
                "SUBJECT_CODE": {
                  "address": "A",
                  "type": "str"
                },
                "SECURITY_NAME": {
                  "address": "B",
                  "type": "str"
                },
                "MARKET_VALUE": {
                  "address": "F",
                  "type": "number"
                }
              }
            }
          ]
        }
      ]
    }
  ],
  "products": [
    {
      "table": "PRODUCT_INDEX",
      "values": {
        "BUSI_DATE": "$BUSI_DATE",
        "PRODUCT_CODE": "$PRODUCT_CODE",
        "TOTAL_ASSET": {
          "address": "F20",
          "type": "number"
        }
      }
    }
  ]
}
```

### 顶层配置

| 字段 | 说明 |
| --- | --- |
| `subject_code_column` | 科目代码所在列，例如 `A` |
| `spare_subject_code_column` | 主科目列为空时使用的备用列 |
| `sheet_name` | 指定工作表名称；不设置时读取默认工作表 |
| `raise_index_out_range_error` | 单元格越界时是否抛出异常，默认 `true` |
| `env` | 全局字段，可在后续配置中通过 `$字段名` 引用 |
| `positions` | 持仓表解析规则列表 |
| `products` | 产品指标表解析规则列表 |

### 单元格取值

字段值可以是常量、环境变量，也可以是一个取值对象：

```json
{
  "address": "F",
  "subject_code": "11030101",
  "capture_regex": "([0-9.]+)",
  "type": "number",
  "merged_value": "up"
}
```

| 字段 | 说明 |
| --- | --- |
| `address` | 绝对地址如 `F20`，持仓规则中也可使用相对列地址如 `F` |
| `subject_code` | 按科目代码定位行，可与列地址配合使用 |
| `capture_regex` | 用正则表达式提取内容；存在捕获组时取第一个捕获组 |
| `type` | 显式转换为 `number`、`str`、`date` 或 `datetime` |
| `value` | 直接设置固定值，也可引用环境变量 |
| `mapping` | 将原始值映射为目标值 |
| `mapping_rule` | 映射方式：`equals`、`contains` 或 `regex` |
| `merged_value` | 当前单元格为空时向 `up`、`down`、`left` 或 `right` 查找非空值 |
| `formula` | 对取值结果进行表达式计算 |
| `filter_formula` | 在候选取值列表中判断当前取值是否生效 |
| `subject_filter_regex` | 在候选取值列表中按当前科目代码过滤 |

`number` 类型支持千分位、百分数以及正负号后的空格，例如 `1,234.56`、`12.5%` 和 `- 20`。

### 持仓规则

每个 `positions` 项对应一张目标表。`default` 设置整张表的默认字段，`groups` 用于组织一组可合并的处理规则，`handlers` 则按 `subject_filter_regex` 匹配估值表行。

`handler` 还支持以下字段：

- `start_row`：开始行号，从 1 开始。
- `stop_row`：结束行号。
- `merge_keys`：多个 handler 合并记录时使用的字段；连接数据库时默认使用目标表主键。
- `post_filter_formula`：字段读取完成后决定是否保留当前记录。

## 输出到数据库

可以在命令行中传入 SQLAlchemy 连接地址：

```bash
uv run vrp ./reports --connection_url "postgresql://user:password@127.0.0.1:5432/valuation"
```

也可以在估值表目录或当前目录创建 `settings.ini`：

```ini
[database]
connection_url = mysql+pymysql://user:password@127.0.0.1:3306/valuation
```

数据库表名来自 `positions[].table` 和 `products[].table`。程序读取目标表结构，根据字段类型转换数据，并按主键更新或插入记录。PostgreSQL 使用批量写入；同一文件的写入在一个事务中完成。

只写数据库、不生成本地 JSON：

```bash
uv run vrp ./reports --connection_url "postgresql://user:password@127.0.0.1:5432/valuation" --nofile
```

openGauss 连接可在查询参数中指定 schema：

```text
opengauss://user:password@127.0.0.1:5432/valuation?schema=public
```

## 辅助工具

### 生成科目清单

扫描目录中的估值表并生成 `code.xlsx`：

```bash
uv run tools gen_code ./reports -c config.json
```

### 生成配置模板

根据数据库表结构生成 `config.json`：

```bash
uv run tools config_template \
  --connection_url "postgresql://user:password@127.0.0.1:5432/valuation" \
  --position_tables "POSITION_DETAIL" \
  --product_tables "PRODUCT_INDEX"
```

多个持仓表或产品表使用逗号分隔。生成的模板会为非空字段填入与数据库类型相符的初始值，之后再补充单元格地址和科目匹配规则。

## Python 调用

```python
from vrp.run import process_file

process_file(
    "./reports/report.xlsx",
    config="./config.json",
    connection_url=None,
    nofile=False,
    debug=False,
)
```

## 开发与构建

安装测试依赖：

```bash
uv sync --extra test
```

运行测试：

```bash
uv run pytest
```

Windows 下构建单文件程序：

```bat
build.bat
```

构建结果位于 `dist\vrp.exe`。

构建 Docker 镜像：

```bash
docker build -t tools-vrp .
docker run --rm -v "$PWD/reports:/data" tools-vrp /data
```

## License

[MIT](LICENSE)
