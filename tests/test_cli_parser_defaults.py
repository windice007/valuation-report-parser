from vrp.cli.parser import build_parser


def test_main_parser_defaults_to_current_directory():
    args = build_parser().parse_args([])
    assert args.dir == "." and args.config == "config.json"
