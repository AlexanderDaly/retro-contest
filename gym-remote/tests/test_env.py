import gym
import os
import time
import gym_remote as gr

from . import process_wrapper


class BitEnv(gym.Env):
    def __init__(self):
        self.action_space = gym.spaces.Discrete(8)
        self.observation_space = gym.spaces.Discrete(2)

    def step(self, action):
        assert self.action_space.contains(action)
        observation = action & 1
        reward = float(action & 2)
        done = bool(action & 4)
        return observation, reward, done, {}

    def reset(self):
        return 0


class StepEnv(gym.Env):
    def __init__(self):
        self.action_space = gym.spaces.Discrete(2)
        self.observation_space = gym.spaces.Discrete(1)
        self.reward = 0
        self.done = False

    def step(self, action):
        if not self.done:
            self.reward += 1
        if action:
            self.done = True
        return 0, self.reward, self.done, {}

    def reset(self):
        self.reward = 0
        self.done = False
        return 0


def test_split(process_wrapper):
    env = BitEnv()
    env = process_wrapper(env)

    assert env.step(0) == (0, 0, False, {})
    assert env.step(1) == (1, 0, False, {})
    assert env.step(2) == (0, 2, False, {})
    assert env.step(3) == (1, 2, False, {})
    assert env.step(4) == (0, 0, True, {})


def test_reset(process_wrapper):
    env = StepEnv()
    env = process_wrapper(env)

    assert env.step(0) == (0, 1, False, {})
    assert env.step(0) == (0, 2, False, {})
    assert env.step(1) == (0, 3, True, {})
    assert env.step(0) == (0, 3, True, {})
    assert env.reset() == 0
    assert env.step(0) == (0, 1, False, {})
    assert env.step(0) == (0, 2, False, {})
    assert env.step(1) == (0, 3, True, {})
    assert env.step(0) == (0, 3, True, {})


def test_ts_limit(process_wrapper):
    env = StepEnv()
    env = process_wrapper(env, timestep_limit=5)

    assert env.step(0) == (0, 1, False, {})
    assert env.step(0) == (0, 2, False, {})
    assert env.step(0) == (0, 3, False, {})
    assert env.step(0) == (0, 4, False, {})
    assert env.step(0) == (0, 5, False, {})
    try:
        env.step(0)
    except gr.Bridge.Closed:
        return
    assert False, 'Remote did not shut down'


def test_wc_limit(process_wrapper):
    env = StepEnv()
    env = process_wrapper(env, wallclock_limit=0.1)

    assert env.step(0) == (0, 1, False, {})
    time.sleep(0.2)
    try:
        env.step(0)
    except gr.Bridge.Closed:
        return
    assert False, 'Remote did not shut down'


def test_cleanup(process_wrapper):
    env = BitEnv()
    env = process_wrapper(env)

    assert os.path.exists(os.path.join(env.bridge.base, 'sock'))

    env.close()

    assert not os.path.exists(os.path.join(env.bridge.base, 'sock'))
