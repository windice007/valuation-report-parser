"""Default values applied to loaded parser configuration."""

from vrp.config.schema import ExcelConfig


def init_config(config: ExcelConfig):
    if config.subject_code_column is None:
        config.subject_code_column = "A"
    if config.raise_index_out_range_error is None:
        config.raise_index_out_range_error = True
    return config
