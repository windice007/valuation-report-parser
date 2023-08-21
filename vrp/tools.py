"""
tools
"""
import logging
from types import ModuleType
import os
import argparse
from vrp.base.logger import logger
import time
from vrp.entry import helper, gen_trade, config_template

ENTRYS: list[ModuleType] = [helper, gen_trade, config_template]


def get_prog(m: ModuleType):
    prog = getattr(m, "__PROG__", None)
    if prog:
        return prog
    file = os.path.basename(m.__file__)
    return os.path.splitext(file)[0]


def main():
    app_start_time = time.time()
    parser = argparse.ArgumentParser(
        description="工具程序",
        prog="tools",
        epilog="通过 tools command --help 可以查看每个子命令的具体说明。",
    )
    parser.add_argument(
        "--debug", action="store_true", default=False, help="启用debug模式，会输出更多信息。"
    )
    subparsers = parser.add_subparsers(title="子命令", help="description", dest="command")

    for m in ENTRYS:
        sub_parser = subparsers.add_parser(
            get_prog(m), help=m.__doc__, description=m.__doc__
        )
        set_parser = getattr(m, "set_parser", None)
        if set_parser:
            set_parser(sub_parser)

    args = parser.parse_args()

    logger.info(args)

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    cmd = next((x for x in ENTRYS if get_prog(x) == args.command))
    cmd.process(args)

    logger.info(f"程序处理完成，共耗时{round(time.time()-app_start_time,3)}秒。")


if __name__ == "__main__":
    main()
