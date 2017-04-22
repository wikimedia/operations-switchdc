from switchdc import SwitchdcError
from switchdc.log import log_task_end, log_task_start, logger


class Menu(object):
    """Menu class."""
    DEFAULT_FIRST_ITEM = 1

    def __init__(self, title, parent=None):
        """Menu constructor

        Arguments:
        title  -- the menu title to be show
        parent -- reference to a parent menu if this is a submenu. [optional, default: None]
        """
        self.title = title
        self.parent = parent
        self.items = {}

    @property
    def status(self):
        """Getter for the menu status, returns a string representation of the status of it's tasks."""
        completed, total = Menu.calculate_status(self)
        if completed == total:
            message = 'DONE'
        else:
            message = '{completed}/{total}'.format(completed=completed, total=total)

        return message

    def append(self, item, idx=None):
        """Append an item or a submenu to this menu.

        Arguments:
        item -- the item to append
        idx  -- optional the index at which this item will be found in the menu
        """
        if idx is None:
            if self.items:
                idx = sorted(self.items.keys())[-1] + 1
            else:
                idx = self.DEFAULT_FIRST_ITEM

        if type(item) == Menu:
            item.parent = self
        self.items[idx] = item

    def run(self):
        """For menu run is equivalent to show."""
        self.show()

    def show(self):
        """Print the menu to stdout."""
        print(self.title)

        for idx in sorted(self.items.keys()):
            item = self.items[idx]
            print(' {i: >2} [{status}] {title}'.format(i=idx, title=item.title, status=item.status))

        if self.parent is None:
            print('  q - Quit')
        else:
            print('  b - Back to parent menu')

    @staticmethod
    def calculate_status(menu):
        """Calculate the status of a menu, checking the status of all it's tasks recursively.

        Arguments:
        menu -- the meny for which to calculate the status
        """
        completed = 0
        total = 0
        for item in menu.items.values():
            item_type = type(item)
            if item_type == Menu:
                sub_completed, sub_total = Menu.calculate_status(item)
                completed += sub_completed
                total += sub_total
            elif item_type == Item:
                total += 1
                if item.status != Item.todo:
                    completed += 1

        return completed, total


class Item(object):
    """Menu item class."""

    statuses = ('TODO', 'PASS', 'FAIL')  # Status labels
    todo, success, failed = statuses  # Valid statuses variables

    def __init__(self, name, title, function, args=None, kwargs=None):
        """Item constructor.

        Arguments
        name     -- the name of the module for this task
        title    -- the item's title to be shown in the menu
        function -- the function to call when the task is run
        args     -- the list of positional arguments to pass to the function. [optional, default: None]
        kwargs   -- the dictionary of keyword arguments to pass to the function. [optional, default: None]
        """
        self.name = name
        self.status = self.todo
        self.function = function

        if args is not None:
            self.args = args
        else:
            self.args = ()

        if kwargs is not None:
            self.kwargs = kwargs
        else:
            self.kwargs = {}

        try:
            title = title.format(*self.args, **self.kwargs)
        except (KeyError, IndexError):
            pass  # Leave the title untouched if unable to format it

        self.title = '{title} - {name}'.format(title=title, name=self.name)

    def run(self):
        """Run the item, calling the configured function."""
        log_task_start(self.title)

        try:
            self.function(*self.args, **self.kwargs)
            retval = 0
        except SwitchdcError as e:
            retval = e.message
        except Exception as e:
            retval = 99
            logger.exception('Failed to execute task {task}: {msg}'.format(task=self.name, msg=e.message))

        if retval == 0:
            self.status = self.success
        else:
            self.status = self.failed

        log_task_end(self.status, self.title)

        return retval
