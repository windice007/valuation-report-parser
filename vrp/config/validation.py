"""Lightweight validation for parser configuration."""

from vrp.base.utils import is_position_column_str


def config_errors(config) -> list[str]:
    errors = []
    if config is None:
        return ["配置不能为空"]
    if not is_position_column_str(config.subject_code_column):
        errors.append("subject_code_column 必须是 Excel 列名")
    if config.positions is not None and not isinstance(config.positions, list):
        errors.append("positions 必须是列表")
    if config.products is not None and not isinstance(config.products, list):
        errors.append("products 必须是列表")
    return errors


def is_valid_config(config) -> bool:
    return not config_errors(config)
