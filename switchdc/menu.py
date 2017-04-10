from switchdc import SwitchdcError
from switchdc.log import log_task_end, log_task_start, logger


class Menu(object):
    """Menu class."""

    def __init__(self, title, parent=None):
        """Menu constructor

        Arguments:
        title  -- the menu title to be show
        parent -- reference to a parent menu if this is a submenu. [optional, default: None]
        """
        self.title = title
        self.parent = parent
        self.items = []

    @property
    def status(self):
        """Getter for the menu status, returns a string representation of the status of it's tasks."""
        completed, total = Menu.calculate_status(self)
        return '{completed}/{total}'.format(completed=completed, total=total)

    def append(self, item):
        """Append an item or a submenu to this menu.

        Arguments:
        item -- the item to append
        """
        if type(item) == Menu:
            item.parent = self
        self.items.append(item)

    def run(self):
        """For menu run is equivalent to show."""
        self.show()

    def show(self):
        """Print the menu to stdout."""
        print(self.title)
        for i, item in enumerate(self.items):
            print(' {i: >2} [{status}] {title}'.format(i=i + 1, title=item.title, status=item.status))

        if self.parent is not None:
            print('  b - Back to parent menu')

        print('  q - Quit')

    @staticmethod
    def calculate_status(menu):
        """Calculate the status of a menu, checking the status of all it's tasks recursively.

        Arguments:
        menu -- the meny for which to calculate the status
        """
        completed = 0
        total = 0
        for item in menu.items:
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
        self.title = title
        self.status = self.todo
        self.function = function
        if args is not None:
            self.args = args
        else:
            self.args = []
        if kwargs is not None:
            self.kwargs = kwargs
        else:
            self.kwargs = {}

    def run(self):
        """Run the item calling the configured function."""
        params = ', '.join(self.args + ['='.join([str(k), str(v)]) for k, v in self.kwargs.iteritems()])
        task_desc = '{name}({params})'.format(name=self.name, params=params)
        log_task_start(task_desc, self.title)

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
            message = 'Successfully completed'
        else:
            self.status = self.failed
            message = 'Failed to execute'

        log_task_end(task_desc, message)

        return retval
