# -*- coding: utf-8 -*-
import signal
from functools import wraps


def timeout(seconds:int):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Define the handler for the alarm signal
            def handler(signum, frame):
                raise TimeoutError(f"Function '{func.__name__}' timed out after {seconds} seconds.")

            # Set the signal handler and the alarm
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds)

            try:
                result = func(*args, **kwargs)
            finally:
                # Disable the alarm regardless of success or failure
                signal.alarm(0)
            return result

        return wrapper

    return decorator