import os


def is_dry_run():
    return os.getenv('SWITCHDC_DRY_RUN') == '1'
