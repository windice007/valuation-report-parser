import json

from base.db_mysql import obj_json_default
from excel import process_excel_file_data as process
from excel.utils import obj_json_hook


if __name__ == "__main__":

    file = "d:/纯固收产品2估值表2021-07-02.xls"
    with open('config.json', 'r', encoding="utf-8") as f:
        config = json.load(f, object_hook=obj_json_hook)
        vpd = process(file, config)
        with open('result.json', 'w', encoding="utf-8") as writer:
            json.dump({"positions": list(vpd.details.values()), "product": vpd.product}, writer,  default=obj_json_default,
                      indent=2, ensure_ascii=False)
