Timeout-Timer
===============

.. image:: https://img.shields.io/pypi/v/timeout-timer.svg
    :alt: PyPI version
    :target: https://pypi.org/project/timeout-timer/

.. image:: https://img.shields.io/pypi/pyversions/timeout-timer.svg
    :alt: Supported Python versions
    :target: https://pypi.org/project/timeout-timer/

Installation
--------------
::

    python setup.py install

Timeout Timer
--------------
    Add a py timeout function to a function or statement and raise a exception if time limit runs out, can work as
    a context or decorator, support loop nesting and should use diff exception class, if use signal timer,
    outside timer will fired after the inside signal timer finish the work(raise exception or normal finish).

    Support signal timeout timer and thread timeout timer, signal timer can only work on main thread, if not on main thread use
    thread timer, thread timer may cost longer time than time out seconds settled if the user's function is busy
    in a system call (time.sleep(), socket.accept()...), exception will fired after system call done.

Usage
--------------
support nested loop
::

    from timeout_timer import timeout, TimeoutInterrupt

    class TimeoutInterruptNested(TimeoutInterrupt):
        pass

    def test_timeout_nested_loop_both_timeout(timer="thread"):
        cnt = 0
        try:
            with timeout(5, timer=timer):
                try:
                    with timeout(2, timer=timer, exception=TimeoutInterruptNested):
                        sleep(2)
                except TimeoutInterruptNested:
                    cnt += 1
                time.sleep(10)
        except TimeoutInterrupt:
            cnt += 1
        assert cnt == 2

use as decorator
::

    @timeout(2):
    def f():
        time.sleep(3)
        time.sleep(2)

License
-------

Code released under the `MIT license <http://en.wikipedia.org/wiki/MIT_License>`_
