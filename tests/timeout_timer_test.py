# coding: utf-8
from timeout_timer import timeout, TimeoutInterrupt
import time

import pytest


class TimeoutInterruptNested(TimeoutInterrupt):
    pass


@pytest.fixture(params=["signal", "thread"])
def timer(request):
    return request.param


def sleep(s):
    time.sleep(s)
    time.sleep(s)


def test_timeout_no_seconds(timer):
    is_timeout = None
    try:
        with timeout(0, timer=timer) as f:
            f(sleep, 1)
    except TimeoutInterrupt:
        is_timeout = True
    assert not is_timeout


def test_timeout_seconds(timer):
    is_timeout = None
    try:
        with timeout(1, timer=timer) as f:
            f(sleep, 2)
    except TimeoutInterrupt:
        is_timeout = True
    assert is_timeout


def test_timeout_nested_loop_inside_timeout(timer):
    try:
        def s():
            try:
                with timeout(2, timer=timer, exception=TimeoutInterruptNested) as f2:
                    f2(sleep, 3)
            except TimeoutInterruptNested:
                return True

        with timeout(10, timer=timer) as f:
            is_timeout = f(s)

    except TimeoutInterrupt:
        is_timeout = "out alert"
    assert is_timeout is True


def test_timeout_nested_loop_outsite_timeout(timer):
    try:
        def s():
            try:
                with timeout(10, timer=timer, exception=TimeoutInterruptNested) as f2:
                    f2(sleep, 3)
            except TimeoutInterruptNested:
                return True

        with timeout(2, timer=timer) as f:
            is_timeout = f(s)

    except TimeoutInterrupt:
        is_timeout = False
    assert is_timeout is False


def test_timeout_nested_loop_both_timeout(timer):
    cnt = []
    try:
        def s():
            try:
                with timeout(2, timer=timer, exception=TimeoutInterruptNested) as f2:
                    f2(sleep, 2)
            except TimeoutInterruptNested:
                cnt.append(1)
            time.sleep(10)
            cnt.append(0)

        with timeout(5, timer=timer) as f:
            f(s)
    except TimeoutInterrupt:
        cnt.append(1)
    assert sum(cnt) == 2
