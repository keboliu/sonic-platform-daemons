"""
Mock platform module for pwmd unit tests
"""


class MockPwm:
    """Mock PWM class for testing"""

    def __init__(self, name='pwm', value=128, min_threshold=0, max_threshold=255):
        self._name = name
        self._value = value
        self._min_threshold = min_threshold
        self._max_threshold = max_threshold

    def get_name(self):
        return self._name

    def get_pwm_value(self):
        return self._value

    def get_pwm_min_threshold(self):
        return self._min_threshold

    def get_pwm_max_threshold(self):
        return self._max_threshold

    def set_pwm_value(self, value):
        """Helper method for testing to set PWM value"""
        self._value = value


class MockChassis:
    """Mock Chassis class for testing"""

    def __init__(self):
        self._pwm = MockPwm()

    def get_pwm(self):
        return self._pwm


class MockPlatform:
    """Mock Platform class for testing"""

    def __init__(self):
        self._chassis = MockChassis()

    def get_chassis(self):
        return self._chassis
