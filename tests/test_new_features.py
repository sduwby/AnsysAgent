"""
新增功能单元测试。

测试范围：
1. signal_timeout 装饰器（跨平台超时保护）
2. aedt_state 状态管理器
3. 线程安全检测函数
"""

import unittest
import time
import sys
import platform
from unittest.mock import patch, MagicMock

# 测试 signal_timeout
from tools.utils import signal_timeout, TimeoutError


class TestSignalTimeout(unittest.TestCase):
    """测试 signal_timeout 装饰器。"""
    
    def test_timeout_does_not_trigger_when_function_completes_fast(self):
        """快速完成的函数不会触发超时。"""
        @signal_timeout(2)
        def fast_function():
            time.sleep(0.1)
            return "success"
        
        result = fast_function()
        self.assertEqual(result, "success")
    
    def test_timeout_triggers_when_function_too_slow(self):
        """慢函数会触发超时异常。"""
        @signal_timeout(1)
        def slow_function():
            time.sleep(2)
            return "should_not_reach"
        
        with self.assertRaises(TimeoutError):
            slow_function()
    
    def test_timeout_works_with_arguments(self):
        """超时装饰器支持带参数的函数。"""
        @signal_timeout(2)
        def add(a, b):
            return a + b
        
        result = add(3, 5)
        self.assertEqual(result, 8)
    
    def test_timeout_works_with_kwargs(self):
        """超时装饰器支持关键字参数。"""
        @signal_timeout(2)
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"
        
        result = greet("World", greeting="Hi")
        self.assertEqual(result, "Hi, World!")
    
    @unittest.skipIf(platform.system() == "Windows", "Windows 使用不同的超时实现")
    def test_unix_signal_alarm_mechanism(self):
        """Unix 系统使用 signal.SIGALRM 机制。"""
        import signal
        
        @signal_timeout(1)
        def func():
            time.sleep(0.5)
            return True
        
        # 验证 signal 模块被正确使用
        with patch('signal.signal') as mock_signal, \
             patch('signal.alarm') as mock_alarm:
            func()
            # 应该调用 signal.signal 两次（设置和恢复）
            self.assertEqual(mock_signal.call_count, 2)
            # 应该调用 signal.alarm 两次（启动和取消）
            self.assertEqual(mock_alarm.call_count, 2)
    
    def test_windows_passthrough(self):
        """Windows 上超时保护不生效，函数直接透传执行。"""
        @signal_timeout(1)
        def func():
            return "passthrough"
        
        with patch('tools.utils.platform.system', return_value="Windows"):
            result = func()
            self.assertEqual(result, "passthrough")


# 测试 aedt_state
from tools.aedt_state import (
    get_manager,
    get_maxwell_app, set_maxwell_app, clear_maxwell_app,
    get_icepak_app, set_icepak_app, clear_icepak_app,
    aedt_session,
)


class TestAedtState(unittest.TestCase):
    """测试 aedt_state 状态管理器。"""
    
    def setUp(self):
        """每个测试前清理状态。"""
        clear_maxwell_app()
        clear_icepak_app()
    
    def test_get_app_returns_none_when_not_set(self):
        """未设置时返回 None。"""
        app = get_maxwell_app()
        self.assertIsNone(app)
    
    def test_set_and_get_app(self):
        """设置后可以获取应用实例。"""
        mock_app = MagicMock()
        set_maxwell_app(mock_app)
        
        retrieved_app = get_maxwell_app()
        self.assertEqual(retrieved_app, mock_app)
    
    def test_clear_app(self):
        """清除后应用实例为 None。"""
        mock_app = MagicMock()
        set_maxwell_app(mock_app)
        
        clear_maxwell_app()
        retrieved_app = get_maxwell_app()
        self.assertIsNone(retrieved_app)
    
    def test_different_app_types_are_independent(self):
        """不同类型的应用相互独立。"""
        mock_maxwell = MagicMock()
        mock_icepak = MagicMock()
        
        set_maxwell_app(mock_maxwell)
        set_icepak_app(mock_icepak)
        
        self.assertEqual(get_maxwell_app(), mock_maxwell)
        self.assertEqual(get_icepak_app(), mock_icepak)
    
    def test_aedt_session_context_manager(self):
        """测试 aedt_session 上下文管理器。"""
        mock_app = MagicMock()
        
        with patch('tools.aedt_state.Maxwell') as mock_maxwell_class:
            mock_maxwell_class.return_value = mock_app
            
            with aedt_session("maxwell") as app:
                self.assertEqual(app, mock_app)
                self.assertEqual(get_maxwell_app(), mock_app)
            
            # 退出上下文后应用应被清除
            self.assertIsNone(get_maxwell_app())
    
    def test_aedt_session_invalid_app_type(self):
        """无效的应用类型应抛出异常。"""
        with self.assertRaises(ValueError):
            with aedt_session("invalid_app"):
                pass


if __name__ == "__main__":
    unittest.main()