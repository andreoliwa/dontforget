from datetime import timedelta

__version__ = "0.1.0"


class Task:
    """A task."""
    def __init__(self, name, description=None):
        self.name = name
        self.description = description


class Every:
    """Base class for all recurrence patterns."""
    _next_dt = None

    def __init__(self, dt=None, days=None):
        """Constructor.

        :param dt: A datetime object.
        :param days: Number of days for this recurrence.
        :return:
        """
        self.dt = dt
        self.days = days

    def next(self, count=1):
        """Return the next date(s) for this recurrence.

        :param count: Number of next dates to return (default is 1).
        :return: Next date or a list of dates (if more than one).
        """
        if not self.dt:
            return None

        self._next_dt = self.dt

        def calculate_next():
            self._next_dt = self._next_dt + timedelta(days=self.days)
            return self._next_dt
        dates_list = [calculate_next() for _ in range(count)]
        return dates_list if len(dates_list) > 1 else dates_list[0]


class Daily(Every):
    """Daily recurrence."""
    def __init__(self, dt=None, days=1):
        super(Daily, self).__init__(dt, days)
