# coding: utf-8
import signal
import time
from functools import wraps, partial
import threading
import ctypes
import inspect


class TimeoutInterrupt(BaseException):
    """inherit from baseException in cased captured by board Exception（eg: except Exception） in user program"""

    def __init__(self, value=""):
        self.value = str(value)

    def __str__(self):
        return self.value


class TimeoutTimer(object):
    """
    Add a timeout function to a function or statement and raise a exception if time limit runs out ,
    it support loop nesting when timer worked as loop nesting, if use signal timer, it will fire after the inside
    signal timer finish the work.

    Signal timer can only work on main thread, if not use thread timer, thread timer may cost longer time than
    time out seconds if the timer's sub thread(user's function) is busy in a system call (time.sleep(),
    socket.accept()...), exception will fired after system call done

    usage:  it can work like a context or a decorator eg
             with TimeoutTimer(2) as f:   or    @TimeoutTimer(2)
                 ...                            def f():
                 f(do something)                    ... do something
                 with TimeoutTimer(1):
                    f(do something)

            if use signal timer it can simplify like:
            with TimeoutTimer(2):
                ... do something
    """

    def __new__(cls, *args, **kwargs):
        """
        config witch timer to use
        :param args: 
        :param kwargs: 
        """

        timer = args[1] if len(args) >= 2 else kwargs.get("timer", "signal")
        timeout_seconds = args[0] if len(args) >= 1 else kwargs.get("seconds", 0)

        if timeout_seconds == 0:
            return super(TimeoutTimer, cls).__new__(_DummyTimeoutTimer)
        elif timer == "signal":
            return super(TimeoutTimer, cls).__new__(_SignalTimeoutTimer)
        elif timer == "thread":
            return super(TimeoutTimer, cls).__new__(_ThreadTimeoutTimer)

        raise NotImplementedError

    def __init__(self, seconds, timer="signal", exception=TimeoutInterrupt, message="", interval=1):
        """
        :param seconds: seconds to raise a timeout exception if user func
        :param timer: the timeout timer to use signal or threading, "signal" or "thread"
        :param exception:  raise exception when timeout
        :param message:  raise exception message when timeout
        :param interval:  seconds to check if the user func is out of time when user thead timer
        """
        self.timeout_seconds = seconds
        self.exception_class = exception
        self.exception_message = message
        self.timer = timer
        self.interval = interval

    def __enter__(self):
        """
        @rtype: function
        """
        self.set()
        return self._exec_func

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cancel()

    def __call__(self, func):
        """ act as a decorator """
        @wraps(func)
        def f(*args, **kwargs):
            self.set()
            try:
                return self._exec_func(func, *args, **kwargs)
            finally:
                self.cancel()

        return f

    def _exec_func(self, func, *args, **kwargs):
        """the func wrapper to exec user func"""
        raise NotImplementedError

    def set(self):
        """do something before exec user func"""
        raise NotImplementedError

    def cancel(self):
        """do something after exec user func"""
        raise NotImplementedError


class _SignalTimeoutTimer(TimeoutTimer):
    def __init__(self, *args, **kwargs):
        super(_SignalTimeoutTimer, self).__init__(*args, **kwargs)
        # params for signal
        self.signal_ori_func = None
        self.signal_ori_timer = 0
        self.st = 0

    def _exec_func(self, func, *args, **kwargs):
        return func(*args, **kwargs)

    def set(self):
        self.st = time.time()
        self.signal_ori_func = signal.signal(signal.SIGALRM, self.timeout_callback)
        self.signal_ori_timer = signal.setitimer(signal.ITIMER_REAL, self.timeout_seconds)

    def cancel(self):
        nt = self.signal_ori_timer[0]
        if nt > 0 and self.st > 0:
            nt = nt - (time.time() - self.st)
        if nt < 0:  # if ori SIGALRM func is timeout  fire it immediately
            signal.signal(signal.SIGALRM, self.signal_ori_func)
            signal.raise_signal(signal.SIGALRM)
        else:
            signal.setitimer(signal.ITIMER_REAL, nt)
            signal.signal(signal.SIGALRM, self.signal_ori_func)

    def timeout_callback(self, signum, frame):
        """signal callback"""
        raise self.exception_class(self.exception_message or str(frame))


class _ThreadTimeoutTimer(TimeoutTimer):
    """
    thread.stop: If the thread is busy in a system call (time.sleep(),
        socket.accept(), ...), the exception is simply ignored util the sleep have done
    so the thread timer's cost time may longer than time out seconds if there is a the thread is busy in a system call
    """

    def __init__(self, *args, **kwargs):
        super(_ThreadTimeoutTimer, self).__init__(*args, **kwargs)

    def _exec_func(self, func, *args, **kwargs):
        _out_time = time.time() + self.timeout_seconds
        tt = _TimerThread(self.exception_class)
        tt.set_func(partial(func, *args, **kwargs))
        tt.setDaemon(True)
        tt.start()
        stop_fired = False
        # wait for task done, it stop may delayed when thread is busy in
        # a system call (time.sleep(), socket.accept(), ...)
        while not tt.func_done:
            if (not stop_fired) and _out_time <= time.time():
                stop_fired = True
                tt.stop()
            else:
                time.sleep(self.interval)

        if tt.error:
            raise tt.error
        res = tt.result
        return res

    def set(self):
        pass

    def cancel(self):
        pass


class _DummyTimeoutTimer(TimeoutTimer):
    """
    thread.stop: If the thread is busy in a system call (time.sleep(),
        socket.accept(), ...), the exception is simply ignored util the sleep have done
    so the thread timer's cost time may longer than time out seconds if there is a the thread is busy in a system call
    """

    def __init__(self, *args, **kwargs):
        super(_DummyTimeoutTimer, self).__init__(*args, **kwargs)

    def _exec_func(self, func, *args, **kwargs):
        return func(*args, **kwargs)

    def set(self):
        pass

    def cancel(self):
        pass


def _async_raise(tid, exctype):
    '''Raises an exception in the threads with id tid'''
    if not inspect.isclass(exctype):
        raise TypeError("Only types can be raised (not instances)")
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid),
                                                     ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # "if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


class StoppableThread(threading.Thread):
    """ thread stop Based on Philippe F's answer of
     https://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread

     Attetion: If the thread is busy in a system call (time.sleep(),
        socket.accept(), ...), the exception is simply ignored util the sleep have done."""

    def stop(self, exception):
        self.raiseExc(exception)

    @property
    def thread_id(self):
        """determines this (self's) thread id

        CAREFUL: this function is executed in the context of the caller
        thread, to get the identity of the thread represented by this
        instance.
        """
        if not self.is_alive():
            raise threading.ThreadError("the thread is not active")

        # do we have it cached?
        if hasattr(self, "_thread_id"):
            return self._thread_id

        # no, look for it in the _active dict
        for tid, tobj in threading._active.items():
            if tobj is self:
                self._thread_id = tid
                return tid

        # TODO: in python 2.6, there's a simpler way to do: self.ident
        raise AssertionError("could not determine the thread's id")

    def raiseExc(self, exc_type):
        """Raises the given exception type in the context of this thread.

        If the thread is busy in a system call (time.sleep(),
        socket.accept(), ...), the exception is simply ignored.

        If you are sure that your exception should terminate the thread,
        one way to ensure that it works is:

            t = ThreadWithExc( ... )
            ...
            t.raiseExc( SomeException )
            while t.isAlive():
                time.sleep( 0.1 )
                t.raiseExc( SomeException )

        If the exception is to be caught by the thread, you need a way to
        check that your thread has caught it.

        CAREFUL: this function is executed in the context of the
        caller thread, to raise an exception in the context of the
        thread represented by this instance.
        """
        try:
            _async_raise(self.thread_id, exc_type)
        except SystemError:
            return False
        return True


class _TimerThread(StoppableThread):
    """
    thread timer's cost time may longer than
    time out seconds if the sub thread(user's func) is busy in a system call ,  will fired after system call  done
    """

    def __init__(self, timeout_class=TimeoutInterrupt):
        super(_TimerThread, self).__init__()

        self.func = None
        self.is_timeout = False
        self.error = None
        self.result = None
        self.exception_class = timeout_class
        self.func_done = False

    def run(self):
        try:
            self.result = self.func()
        except self.exception_class as e:
            self.is_timeout = True
            self.error = e
        except Exception as e:
            self.error = e
        finally:
            self.func_done = True

    def set_func(self, func):
        self.func = func

    def stop(self, exception=None):
        super(_TimerThread, self).stop(exception or self.exception_class)

if __name__ == "__main__":
    def f():
        while True:
            time.sleep(10)
            time.sleep(50)


    # cost 5s
    t = time.time()
    try:
        with TimeoutTimer(5) as ff:
            ff(f)
    except TimeoutInterrupt as e:
        print(e)
    finally:
        print(time.time() - t)

    # cost 10s
    try:
        t = time.time()
        with TimeoutTimer(5, timer="thread") as ff:
            ff(f)
    except TimeoutInterrupt as e:
        print(e)
    finally:
        print(time.time() - t)
