"""
Test pwmd daemon
"""

import os
import sys
from unittest import mock

# Add tests directory to path for mock imports
test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
sys.path.insert(0, modules_path)
sys.path.insert(0, os.path.join(test_path, 'mocked_libs'))

# Mock modules before importing pwmd
sys.modules['swsscommon'] = __import__('swsscommon')
sys.modules['swsscommon.swsscommon'] = __import__('swsscommon.swsscommon')


class TestPwmStatus:
    """Test PwmStatus class"""

    def test_init(self):
        """Test PwmStatus initialization"""
        from tests.mock_platform import MockPwm

        with mock.patch.dict(sys.modules, {'sonic_platform.platform': mock.MagicMock()}):
            # Import after mocking
            sys.path.insert(0, os.path.join(modules_path, 'scripts'))
            import importlib
            pwmd_module = importlib.import_module('pwmd')

            pwm = MockPwm()
            logger = mock.MagicMock()
            status = pwmd_module.PwmStatus(logger, pwm)

            assert status.current_value == 0
            assert status.min_value is None
            assert status.max_value is None
            assert status.status == pwmd_module.PWM_STATUS_OK

    def test_update_value(self):
        """Test PwmStatus.update_value()"""
        from tests.mock_platform import MockPwm

        with mock.patch.dict(sys.modules, {'sonic_platform.platform': mock.MagicMock()}):
            sys.path.insert(0, os.path.join(modules_path, 'scripts'))
            import importlib
            pwmd_module = importlib.import_module('pwmd')

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
        from tests.mock_platform import MockPwm

        with mock.patch.dict(sys.modules, {'sonic_platform.platform': mock.MagicMock()}):
            sys.path.insert(0, os.path.join(modules_path, 'scripts'))
            import importlib
            pwmd_module = importlib.import_module('pwmd')

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
            sys.path.insert(0, os.path.join(modules_path, 'scripts'))
            import importlib
            pwmd_module = importlib.import_module('pwmd')

            result = pwmd_module.try_get(lambda: 42, default=0)
            assert result == 42

    def test_try_get_not_implemented(self):
        """Test try_get with NotImplementedError"""
        with mock.patch.dict(sys.modules, {'sonic_platform.platform': mock.MagicMock()}):
            sys.path.insert(0, os.path.join(modules_path, 'scripts'))
            import importlib
            pwmd_module = importlib.import_module('pwmd')

            def raise_not_implemented():
                raise NotImplementedError()

            result = pwmd_module.try_get(raise_not_implemented, default=99)
            assert result == 99

    def test_try_get_none_returns_default(self):
        """Test try_get when callback returns None"""
        with mock.patch.dict(sys.modules, {'sonic_platform.platform': mock.MagicMock()}):
            sys.path.insert(0, os.path.join(modules_path, 'scripts'))
            import importlib
            pwmd_module = importlib.import_module('pwmd')

            result = pwmd_module.try_get(lambda: None, default=99)
            assert result == 99


class TestDaemonPwmd:
    """Test DaemonPwmd class"""

    @mock.patch('sonic_py_common.daemon_base.db_connect')
    @mock.patch('sonic_py_common.daemon_base.DaemonBase.__init__')
    def test_daemon_init(self, mock_daemon_init, mock_db_connect):
        """Test DaemonPwmd initialization"""
        from tests.mock_platform import MockPlatform

        mock_daemon_init.return_value = None
        mock_db_connect.return_value = mock.MagicMock()

        with mock.patch.dict(sys.modules, {
            'sonic_platform': mock.MagicMock(),
            'sonic_platform.platform': mock.MagicMock()
        }):
            sys.path.insert(0, os.path.join(modules_path, 'scripts'))
            import importlib
            pwmd_module = importlib.import_module('pwmd')

            # Mock platform
            mock_platform = MockPlatform()
            pwmd_module.sonic_platform = mock.MagicMock()
            pwmd_module.sonic_platform.platform.Platform.return_value = mock_platform

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
        from tests.mock_platform import MockPlatform, MockPwm

        mock_daemon_init.return_value = None
        mock_db = mock.MagicMock()
        mock_db_connect.return_value = mock_db

        with mock.patch.dict(sys.modules, {
            'sonic_platform': mock.MagicMock(),
            'sonic_platform.platform': mock.MagicMock()
        }):
            sys.path.insert(0, os.path.join(modules_path, 'scripts'))
            import importlib
            pwmd_module = importlib.import_module('pwmd')

            # Create mock PWM with specific values
            mock_pwm = MockPwm(name='test_pwm', value=128, min_threshold=0, max_threshold=255)
            mock_chassis = mock.MagicMock()
            mock_chassis.get_pwm.return_value = mock_pwm

            mock_platform = mock.MagicMock()
            mock_platform.get_chassis.return_value = mock_chassis

            pwmd_module.sonic_platform = mock.MagicMock()
            pwmd_module.sonic_platform.platform.Platform.return_value = mock_platform

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
        from tests.mock_platform import MockPwm

        mock_daemon_init.return_value = None
        mock_db = mock.MagicMock()
        mock_db_connect.return_value = mock_db

        with mock.patch.dict(sys.modules, {
            'sonic_platform': mock.MagicMock(),
            'sonic_platform.platform': mock.MagicMock()
        }):
            sys.path.insert(0, os.path.join(modules_path, 'scripts'))
            import importlib
            pwmd_module = importlib.import_module('pwmd')

            # Create mock PWM with value outside threshold
            mock_pwm = MockPwm(name='test_pwm', value=300, min_threshold=0, max_threshold=255)
            mock_chassis = mock.MagicMock()
            mock_chassis.get_pwm.return_value = mock_pwm

            mock_platform = mock.MagicMock()
            mock_platform.get_chassis.return_value = mock_chassis

            pwmd_module.sonic_platform = mock.MagicMock()
            pwmd_module.sonic_platform.platform.Platform.return_value = mock_platform

            with mock.patch.object(pwmd_module.DaemonPwmd, 'set_min_log_priority_info'):
                with mock.patch.object(pwmd_module.DaemonPwmd, 'log_info'):
                    with mock.patch.object(pwmd_module.DaemonPwmd, 'log_error') as mock_log_error:
                        daemon = pwmd_module.DaemonPwmd('pwmd')

                        # Update PWM data - should trigger error log
                        daemon._update_single_pwm_data()

                        # Verify error was logged
                        assert daemon.pwm_status.status == pwmd_module.PWM_STATUS_NOT_OK
                        mock_log_error.assert_called()
