"""
Test pwmd daemon
"""

import os
import sys
import importlib.util
from unittest import mock

# Add tests directory to path for mock imports
test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, 'scripts')
sys.path.insert(0, modules_path)
sys.path.insert(0, os.path.join(test_path, 'mocked_libs'))

# Mock modules before importing pwmd
sys.modules['swsscommon'] = __import__('swsscommon')
sys.modules['swsscommon.swsscommon'] = __import__('swsscommon.swsscommon')

from .mock_platform import MockPwm, MockPlatform


def load_pwmd_module():
    """Load the pwmd script as a module"""
    # Remove cached pwmd module to ensure fresh load with current mocks
    if 'pwmd' in sys.modules:
        del sys.modules['pwmd']

    pwmd_path = os.path.join(scripts_path, 'pwmd')
    spec = importlib.util.spec_from_loader('pwmd', loader=None, origin=pwmd_path)
    pwmd_module = importlib.util.module_from_spec(spec)
    with open(pwmd_path, 'r') as f:
        code = compile(f.read(), pwmd_path, 'exec')
        exec(code, pwmd_module.__dict__)
    sys.modules['pwmd'] = pwmd_module
    return pwmd_module


class TestPwmStatus:
    """Test PwmStatus class"""

    def test_init(self):
        """Test PwmStatus initialization"""
        with mock.patch.dict(sys.modules, {'sonic_platform.platform': mock.MagicMock()}):
            pwmd_module = load_pwmd_module()

            pwm = MockPwm()
            logger = mock.MagicMock()
            status = pwmd_module.PwmStatus(logger, pwm)

            assert status.current_value == 0
            assert status.min_value is None
            assert status.max_value is None
            assert status.status == pwmd_module.PWM_STATUS_OK

    def test_update_value(self):
        """Test PwmStatus.update_value()"""
        with mock.patch.dict(sys.modules, {'sonic_platform.platform': mock.MagicMock()}):
            pwmd_module = load_pwmd_module()

            pwm = MockPwm()
            logger = mock.MagicMock()
            status = pwmd_module.PwmStatus(logger, pwm)

            # First update sets min and max
            result = status.update_value(100)
            assert result is True
            assert status.current_value == 100
            assert status.min_value == 100
            assert status.max_value == 100

            # Update with lower value updates min only
            result = status.update_value(50)
            assert result is True
            assert status.current_value == 50
            assert status.min_value == 50
            assert status.max_value == 100

            # Update with higher value updates max only
            result = status.update_value(150)
            assert result is True
            assert status.current_value == 150
            assert status.min_value == 50
            assert status.max_value == 150

            # Update with value in between doesn't update min/max
            result = status.update_value(100)
            assert result is False
            assert status.current_value == 100
            assert status.min_value == 50
            assert status.max_value == 150

    def test_check_threshold(self):
        """Test PwmStatus.check_threshold()"""
        with mock.patch.dict(sys.modules, {'sonic_platform.platform': mock.MagicMock()}):
            pwmd_module = load_pwmd_module()

            pwm = MockPwm()
            logger = mock.MagicMock()
            status = pwmd_module.PwmStatus(logger, pwm)

            # Value within threshold
            status.update_value(100)
            result = status.check_threshold(0, 255)
            assert status.status == pwmd_module.PWM_STATUS_OK
            assert status.is_ok() is True

            # Value below minimum threshold
            status.update_value(-1)
            result = status.check_threshold(0, 255)
            assert result is True  # Status changed
            assert status.status == pwmd_module.PWM_STATUS_NOT_OK
            assert status.is_ok() is False

            # Value above maximum threshold
            status.status = pwmd_module.PWM_STATUS_OK
            status.update_value(300)
            result = status.check_threshold(0, 255)
            assert result is True  # Status changed
            assert status.status == pwmd_module.PWM_STATUS_NOT_OK
            assert status.is_ok() is False

            # Value at exact minimum threshold (OK)
            status.status = pwmd_module.PWM_STATUS_NOT_OK
            status.update_value(0)
            result = status.check_threshold(0, 255)
            assert result is True  # Status changed
            assert status.status == pwmd_module.PWM_STATUS_OK

            # Value at exact maximum threshold (OK)
            status.update_value(255)
            result = status.check_threshold(0, 255)
            assert result is False  # Status unchanged
            assert status.status == pwmd_module.PWM_STATUS_OK


class TestTryGet:
    """Test try_get helper function"""

    def test_try_get_success(self):
        """Test try_get with successful callback"""
        with mock.patch.dict(sys.modules, {'sonic_platform.platform': mock.MagicMock()}):
            pwmd_module = load_pwmd_module()

            result = pwmd_module.try_get(lambda: 42, default=0)
            assert result == 42

    def test_try_get_not_implemented(self):
        """Test try_get with NotImplementedError"""
        with mock.patch.dict(sys.modules, {'sonic_platform.platform': mock.MagicMock()}):
            pwmd_module = load_pwmd_module()

            def raise_not_implemented():
                raise NotImplementedError()

            result = pwmd_module.try_get(raise_not_implemented, default=99)
            assert result == 99

    def test_try_get_none_returns_default(self):
        """Test try_get when callback returns None"""
        with mock.patch.dict(sys.modules, {'sonic_platform.platform': mock.MagicMock()}):
            pwmd_module = load_pwmd_module()

            result = pwmd_module.try_get(lambda: None, default=99)
            assert result == 99


class TestDaemonPwmd:
    """Test DaemonPwmd class"""

    def _create_mock_platform_module(self, mock_pwm):
        """Create a properly configured mock platform module"""
        mock_chassis = mock.MagicMock()
        mock_chassis.get_pwm.return_value = mock_pwm

        mock_platform_instance = mock.MagicMock()
        mock_platform_instance.get_chassis.return_value = mock_chassis

        # Create mock platform module and configure Platform() to return our instance
        mock_platform_module = mock.MagicMock()
        mock_platform_module.Platform.return_value = mock_platform_instance

        # Create parent mock and link to platform module
        mock_sonic_platform = mock.MagicMock()
        mock_sonic_platform.platform = mock_platform_module

        return mock_sonic_platform, mock_platform_module

    @mock.patch('sonic_py_common.daemon_base.db_connect')
    @mock.patch('sonic_py_common.daemon_base.DaemonBase.__init__')
    def test_daemon_init(self, mock_daemon_init, mock_db_connect):
        """Test DaemonPwmd initialization"""
        mock_daemon_init.return_value = None
        mock_db_connect.return_value = mock.MagicMock()

        # Create mock PWM
        mock_pwm = MockPwm()
        mock_sonic_platform, mock_platform_module = self._create_mock_platform_module(mock_pwm)

        with mock.patch.dict(sys.modules, {
            'sonic_platform': mock_sonic_platform,
            'sonic_platform.platform': mock_platform_module
        }):
            pwmd_module = load_pwmd_module()

            with mock.patch.object(pwmd_module.DaemonPwmd, 'set_min_log_priority_info'):
                with mock.patch.object(pwmd_module.DaemonPwmd, 'log_info'):
                    daemon = pwmd_module.DaemonPwmd('pwmd')

                    assert daemon.pwm is not None
                    assert daemon.pwm_status is not None
                    assert daemon.first_run is True

    @mock.patch('sonic_py_common.daemon_base.db_connect')
    @mock.patch('sonic_py_common.daemon_base.DaemonBase.__init__')
    def test_update_pwm_data(self, mock_daemon_init, mock_db_connect):
        """Test _update_single_pwm_data method"""
        mock_daemon_init.return_value = None
        mock_db = mock.MagicMock()
        mock_db_connect.return_value = mock_db

        # Create mock PWM with specific values
        mock_pwm = MockPwm(name='test_pwm', value=128, min_threshold=0, max_threshold=255)
        mock_sonic_platform, mock_platform_module = self._create_mock_platform_module(mock_pwm)

        with mock.patch.dict(sys.modules, {
            'sonic_platform': mock_sonic_platform,
            'sonic_platform.platform': mock_platform_module
        }):
            pwmd_module = load_pwmd_module()

            with mock.patch.object(pwmd_module.DaemonPwmd, 'set_min_log_priority_info'):
                with mock.patch.object(pwmd_module.DaemonPwmd, 'log_info'):
                    with mock.patch.object(pwmd_module.DaemonPwmd, 'log_notice'):
                        daemon = pwmd_module.DaemonPwmd('pwmd')

                        # Update PWM data
                        daemon._update_single_pwm_data()

                        # Verify status was updated
                        assert daemon.pwm_status.current_value == 128
                        assert daemon.pwm_status.min_value == 128
                        assert daemon.pwm_status.max_value == 128
                        assert daemon.pwm_status.status == pwmd_module.PWM_STATUS_OK

    @mock.patch('sonic_py_common.daemon_base.db_connect')
    @mock.patch('sonic_py_common.daemon_base.DaemonBase.__init__')
    def test_threshold_violation_logging(self, mock_daemon_init, mock_db_connect):
        """Test that threshold violations are logged"""
        mock_daemon_init.return_value = None
        mock_db = mock.MagicMock()
        mock_db_connect.return_value = mock_db

        # Create mock PWM with value outside threshold
        mock_pwm = MockPwm(name='test_pwm', value=300, min_threshold=0, max_threshold=255)
        mock_sonic_platform, mock_platform_module = self._create_mock_platform_module(mock_pwm)

        with mock.patch.dict(sys.modules, {
            'sonic_platform': mock_sonic_platform,
            'sonic_platform.platform': mock_platform_module
        }):
            pwmd_module = load_pwmd_module()

            with mock.patch.object(pwmd_module.DaemonPwmd, 'set_min_log_priority_info'):
                with mock.patch.object(pwmd_module.DaemonPwmd, 'log_info'):
                    with mock.patch.object(pwmd_module.DaemonPwmd, 'log_error') as mock_log_error:
                        daemon = pwmd_module.DaemonPwmd('pwmd')

                        # Update PWM data - should trigger error log
                        daemon._update_single_pwm_data()

                        # Verify error was logged
                        assert daemon.pwm_status.status == pwmd_module.PWM_STATUS_NOT_OK
                        mock_log_error.assert_called()
