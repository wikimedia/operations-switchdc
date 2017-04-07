import argparse
import glob
import importlib
import logging
import os
import sys

from switchdc import get_global_config, log
from switchdc.menu import Item, Menu


def run(menu, dc_from, dc_to):
    """Run the swithcdc interactive menu.

    Arguments:
    menu    -- the Menu instance to use for the run
    dc_from -- the name of the datacenter to migrate from
    dc_to   -- the name of the datacenter to migrate to
    """
    while True:
        print('#--- DATACENTER SWITCHOVER FROM {dc_from} TO {dc_to} ---#'.format(dc_from=dc_from, dc_to=dc_to))
        menu.show()
        try:
            answer = raw_input('>>> ')
        except (EOFError, KeyboardInterrupt):
            print  # Nicer output
            break  # Ctrl+d or Ctrl+c pressed while waiting for input

        if not answer:
            continue
        elif answer == 'q':
            break
        elif answer == 'b':
            menu = menu.parent

        try:
            index = int(answer)
        except Exception:
            print('Invalid answer')
            continue

        if index > 0 and index <= len(menu.items):
            item = menu.items[index - 1]
            if type(item) == Menu:
                menu = item
            elif type(item) == Item:
                rc = item.run()
                if rc != 0:
                    print('FAILED TO RUN TASK: {task}'.format(task=item.name))
        else:
            print('==> Invalid input <==')
            continue

    return 0


def parse_args():
    """Parse command line arguments and return them."""
    parser = argparse.ArgumentParser(description='Datacenter Switchover for Mediawiki')
    parser.add_argument('-f', '--dc-from', required=True, help='Name of the datacenter to migrate **from**')
    parser.add_argument('-t', '--dc-to', required=True, help='Name of the datacenter to migrate **to**')
    parser.add_argument('--task', help='If specified, run this task only in an non-interactive way and exit')
    parser.add_argument(
        '--stage', help='If specified, run all the tasks of this stage in an non-interactive way and exit')
    parser.add_argument(
        '--dry-run', action='store_true', help='Run in dry-run mode, only RO commands will be executed')

    return parser.parse_args()


def generate_menu(dc_from, dc_to):
    """Automatically generate the menu with items and submenus based on the available modules.

    Arguments:
    dc_from -- the name of the datacenter to migrate from
    dc_to   -- the name of the datacenter to migrate to
    """
    menu = Menu('Datacenter switchover automation')
    stage = '00'
    submenu = Menu('Stage 00')

    for module_file in sorted(glob.glob(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'stages', 't[0-9][0-9]_*.py'))):

        module_name = os.path.basename(module_file)[:-3]
        module_stage = module_name[1:3]
        module = importlib.import_module('switchdc.stages.{module_name}'.format(module_name=module_name))

        if module_stage != stage:
            if submenu is not None:
                menu.append(submenu)
            stage = module_stage
            submenu = Menu('Stage {stage}'.format(stage=stage))

        submenu.append(Item(module.__name__, module.__title__, module.execute, args=[dc_from, dc_to]))
    else:
        if submenu is not None:
            menu.append(submenu)

    return menu


def main():
    """Entry point, run the tool."""
    log.setup_logging()
    config = get_global_config()
    if {'tcpircbot_host', 'tcpircbot_port'} <= set(config):
        log.setup_irc(config)
    args = parse_args()
    if args.dry_run:
        os.environ['SWITCHDC_DRY_RUN'] = '1'
        log.irc_logger.setLevel(logging.WARN)
    menu = generate_menu(args.dc_from, args.dc_to)

    rc = 1
    if args.task is not None:
        # Run a single task in non-interactive mode
        # We can't know if the items list counts from 0 or 1,
        # so let's just cycle through all menus
        for submenu in menu.items:
            for item in submenu.items:
                if item.name.split('.')[-1] == args.task:
                    rc = item.run()
                    break
        else:
            print("Unable to find task '{task}'".format(task=args.task))

    elif args.stage is not None:
        # Run all tasks in a stage in non-interactive mode
        stage = int(args.stage)
        if 0 < stage <= len(menu.items):
            for item in menu.items[stage - 1].items:
                rc = item.run()
                if rc != 0:
                    print "Task {name}: {title} failed, aborting execution".format(name=item.name, title=item.title)
                    break
        else:
            print("Unable to find stage '{stage}'".format(stage=args.stage))

    else:
        rc = run(menu, args.dc_from, args.dc_to)  # Run the interactive menu

    return rc


if __name__ == '__main__':
    sys.exit(main())
