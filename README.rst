Installation
============
::

    python setup.py install

Timeout Timer
============
    Add a timeout function to a function or statement and raise a exception if time limit runs out ,
    it support loop nesting when timer worked as loop nesting, if use signal timer, it will fire after the inside
    signal timer finish the work.

    Signal timer can only work on main thread, if not use thread timer, thread timer may cost longer time than
    time out seconds if the timer's sub thread(user's function) is busy in a system call (time.sleep(),
    socket.accept()...), exception will fired after system call done.

Usage
============
support nested loop
::
    try:
        with TimeoutTimer(2, timer="signal") as f:
            f(time.sleep, 0.5)
            with TimeoutTimer(1, timer="signal") as f2:
                f2(time.sleep, 2)
    except TimeoutInterrupt:
        print("timeout triggered")


or use signal timer can simplify
::
    try:
        with TimeoutTimer(2) :
            time.sleep(3)
    except TimeoutInterrupt:
        print("timeout triggered")

or use as decorator
::
    @TimeoutTimer(2):
    def f():
        time.sleep(3)
        time.sleep(2)

License
-------

Code released under the `MIT license <http://en.wikipedia.org/wiki/MIT_License>`_
