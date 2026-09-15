from vrp.cli.parser import build_parser


def test_main_parser_accepts_output_flags():
    args = build_parser().parse_args(["reports", "--nofile", "--debug"])
    assert args.dir == "reports" and args.nofile and args.debug
