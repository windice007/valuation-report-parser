"""Programmatic and parsed-argument job execution."""


def do_job(args):
    from vrp.run import do_job as run_job
    return run_job(args)


def process_file(*args, **kwargs):
    from vrp.run import process_file as run_file
    return run_file(*args, **kwargs)
