import random
import time

def test_pass():
    assert 1 == 1

def test_flaky():
    # intentionally flaky for demo
    assert random.random() > 0.3

def test_slow():
    time.sleep(0.1)
    assert True
