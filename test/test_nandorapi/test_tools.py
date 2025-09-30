import pytest
import unittest
import os
import datetime
import time
from unittest.mock import patch, mock_open

# Assume the provided classes are in a file named 'your_module.py'
from nandorapi.tools import Paging, EndConditions, Output, Timeout


class TestPaging:
    """Tests the Paging class for cursor-based pagination."""

    def test_init(self):
        """Test the initialization of the Paging class."""
        # Test case 1: All parameters provided
        pager1 = Paging(cursor_param="offset", max_results_value=100, cursor_value=50, max_results_param="limit")
        assert pager1.cursor_param == "offset"
        assert pager1.max_results_value == 100
        assert pager1.cursor_value == 50
        assert pager1.state_dict == {"limit": 100}
        assert pager1.live_query is True

        # Test case 2: Default cursor_value
        pager2 = Paging(cursor_param="page", max_results_value=10)
        assert pager2.cursor_value == 0
        assert pager2.state_dict == {}
        assert pager2.live_query is True

        # Test case 3: No max_results_param
        pager3 = Paging(cursor_param="start", max_results_value=25)
        assert pager3.state_dict == {}

    def test_page_generator(self):
        """Test the page generator functionality."""
        pager = Paging(cursor_param="offset", max_results_value=50, max_results_param="limit")
        
        # Test case 1: Yields correct parameters and increments cursor
        generator = pager.page()
        
        params1 = next(generator)
        assert params1 == {"limit": 50, "offset": 0}
        assert pager.cursor_value == 0
        
        params2 = next(generator)
        assert params2 == {"limit": 50, "offset": 50}
        assert pager.cursor_value == 50
        
        # Test case 2: Generator stops after kill_paging is called
        pager.kill_paging()
        with pytest.raises(StopIteration):
            next(generator)
            
    def test_kill_paging(self):
        """Test the kill_paging method."""
        pager = Paging(cursor_param="offset", max_results_value=10)
        assert pager.live_query is True
        
        pager.kill_paging()
        assert pager.live_query is False
        
        # Ensure a killed pager's generator raises StopIteration immediately
        generator = pager.page()
        with pytest.raises(StopIteration):
            next(generator)


class TestEndConditions:
    """Tests the EndConditions class for termination logic."""

    def test_init(self):
        """Test initialization with default and custom values."""
        # Test case 1: Default values
        conditions = EndConditions()
        assert conditions.max_queries == 1_000
        assert conditions.end_date > datetime.datetime.now()
        assert conditions.i == -1

        # Test case 2: Custom values
        future_date = datetime.datetime.now() + datetime.timedelta(seconds=100)
        conditions_custom = EndConditions(max_queries=5, end_date=future_date)
        assert conditions_custom.max_queries == 5
        assert conditions_custom.end_date == future_date
        assert conditions_custom.i == -1

        # Test case 3: None for max_queries
        conditions_none_queries = EndConditions(max_queries=None)
        assert conditions_none_queries.max_queries is None

    def test_bool_operator(self):
        """Test the __bool__ operator for correct logic."""
        # Test case 1: Continues while within limits
        conditions = EndConditions(max_queries=3)
        assert bool(conditions) is True  # i becomes 0
        assert conditions.i == 0
        assert bool(conditions) is True  # i becomes 1
        assert conditions.i == 1
        assert bool(conditions) is True  # i becomes 2
        assert conditions.i == 2
        assert bool(conditions) is False # i becomes 3, limit reached
        assert conditions.i == 3

        # Test case 2: Stops due to date limit
        past_date = datetime.datetime.now() - datetime.timedelta(seconds=1)
        conditions_date = EndConditions(max_queries=1_000, end_date=past_date)
        assert bool(conditions_date) is False # i becomes 0, date limit reached
        assert conditions_date.i == 0

        # Test case 3: No max_queries limit
        conditions_no_limit = EndConditions(max_queries=None)
        for _ in range(100):
            assert bool(conditions_no_limit) is True
        assert conditions_no_limit.i == 99

    def test_integration_with_loop(self):
        """Test EndConditions behavior in a simple loop."""
        conditions = EndConditions(max_queries=3)
        count = 0
        while conditions:
            count += 1
        assert count == 3
        assert conditions.i == 3


class TestOutput:
    """Tests the Output class for file path generation and writing."""

    def test_init_and_make_save_location(self, tmp_path):
        """Test initialization and directory creation."""
        # Test case 1: Default parameters, create a new directory
        # The `tmp_path` fixture provides a temporary directory for tests
        with patch('os.path.exists', return_value=False):
            with patch('os.makedirs') as mock_makedirs:
                output = Output(folder_path=[str(tmp_path), 'test_dir'])
                assert output.i == 0
                assert output.overwrite_safe_mode is True
                mock_makedirs.assert_called_once_with(os.path.join(str(tmp_path), 'test_dir'), exist_ok=True)
                assert '{index}' in output.path_template

        # Test case 2: Overwrite safe mode raises error if path exists
        with patch('os.path.exists', return_value=True):
            with pytest.raises(FileExistsError):
                Output(folder_path=[str(tmp_path), 'existing_dir'])

        # Test case 3: Safe mode off, does not raise error
        with patch('os.path.exists', return_value=True):
            with patch('os.makedirs') as mock_makedirs:
                Output(folder_path=[str(tmp_path), 'existing_dir'], overwrite_safe_mode=False)
                mock_makedirs.assert_called_once_with(os.path.join(str(tmp_path), 'existing_dir'), exist_ok=True)

    def test_format_paths(self):
        """Test the path formatting logic."""
        output = Output(index_length=3, date_format='%Y%m%d', folder_path=['temp'])
        
        # Test case 1: Path with both date and index
        path_template = 'downloads/{date}/file_{index}.txt'
        with patch('datetime.datetime') as mock_dt:
            mock_dt.now.return_value = datetime.datetime(2025, 1, 15)
            formatted_path = output._format_paths(path_template)
            assert formatted_path == 'downloads/20250115/file_000.txt'
            assert output.i == 1
            
        # Test case 2: Path with only index
        path_template_index = 'data_{index}.csv'
        formatted_path_index = output._format_paths(path_template_index)
        assert formatted_path_index == 'data_001.csv'
        assert output.i == 2

        # Test case 3: Path with only date
        path_template_date = 'reports/{date}/report.pdf'
        with patch('datetime.datetime') as mock_dt:
            mock_dt.now.return_value = datetime.datetime(2025, 2, 20)
            formatted_path_date = output._format_paths(path_template_date)
            assert formatted_path_date == 'reports/20250220/report.pdf'
            assert output.i == 2 # Index should not have incremented

    def test_write_bytes(self, tmp_path):
        """Test the write_bytes method."""
        # Create a mock path and object for the test
        temp_dir = tmp_path / 'test_output'
        temp_dir.mkdir()

        # Patch the file existence check for `_make_save_location`
        with patch('os.path.exists', return_value=False):
            # Patch `os.makedirs` to prevent actual directory creation (already done above)
            with patch('os.makedirs'):
                output = Output(folder_path=[str(temp_dir)], output_name='file_{index}.bin')

        # Test case 1: Write a file and check content and path
        with patch('builtins.open', mock_open()) as mock_file:
            data = b'Hello, World!'
            output.write_bytes(data)
            
            # The mocked file open should have been called with the correct path and mode
            expected_path = os.path.join(str(temp_dir), 'file_00000.bin')
            mock_file.assert_called_once_with(expected_path, 'wb')
            
            # Check if the write method was called with the correct data
            mock_file().write.assert_called_once_with(data)
            
            # The index should have incremented
            assert output.i == 1


class TestTimeout:
    """Tests the Timeout class for pausing execution."""

    def test_init_raises_error(self):
        """Test that initialization raises an error without a pause method."""
        with pytest.raises(AttributeError, match='pause_func or pause_seconds must be defined.'):
            Timeout()

    @patch('time.sleep')
    def test_pause_seconds(self, mock_sleep):
        """Test pausing with a fixed number of seconds."""
        timeout = Timeout(pause_seconds=5)
        timeout.pause()
        mock_sleep.assert_called_once_with(5)

    def test_pause_func_with_no_kwargs(self):
        """Test pausing with a custom function without arguments."""
        mock_func = unittest.mock.MagicMock()
        timeout = Timeout(pause_func=mock_func)
        timeout.pause()
        mock_func.assert_called_once()
        
    def test_pause_func_with_kwargs(self):
        """Test pausing with a custom function with arguments."""
        mock_func = unittest.mock.MagicMock()
        timeout = Timeout(pause_func=mock_func, arg1='value1', arg2=10)
        timeout.pause()
        mock_func.assert_called_once_with(arg1='value1', arg2=10)
        
    @patch('time.sleep')
    def test_pause_precedence(self, mock_sleep):
        """Test that pause_seconds takes precedence over pause_func."""
        mock_func = unittest.mock.MagicMock()
        timeout = Timeout(pause_seconds=2, pause_func=mock_func)
        timeout.pause()
        mock_sleep.assert_called_once_with(2)
        mock_func.assert_not_called()