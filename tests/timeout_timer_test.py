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
        with timeout(0, timer=timer):
            sleep(1)
    except TimeoutInterrupt:
        is_timeout = True
    assert not is_timeout


def test_timeout_seconds(timer):
    is_timeout = None
    try:
        with timeout(1, timer=timer):
            sleep(2)
    except TimeoutInterrupt:
        is_timeout = True
    assert is_timeout


def test_timeout_nested_loop_inside_timeout(timer):
    is_timeout = None
    try:
        with timeout(10, timer=timer):
            try:
                with timeout(2, timer=timer, exception=TimeoutInterruptNested):
                    sleep(3)
            except TimeoutInterruptNested:
                is_timeout = True
    except TimeoutInterrupt:
        is_timeout = False
    assert is_timeout is True


def test_timeout_nested_loop_outside_timeout(timer):
    try:
        with timeout(2, timer=timer):
            try:
                with timeout(10, timer=timer, exception=TimeoutInterruptNested):
                    sleep(3)
            except TimeoutInterruptNested:
                is_timeout = True

    except TimeoutInterrupt:
        is_timeout = False
    assert is_timeout is False


def test_timeout_nested_loop_both_timeout(timer):
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
