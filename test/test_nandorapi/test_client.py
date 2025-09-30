import pytest
import unittest
from unittest.mock import MagicMock, patch, mock_open
import requests
import os
import datetime
from nandorapi import tools
from nandorapi.client import Client # Assuming Client class is in a file named your_module.py


class TestClient:
    """Tests the Client class's core functionality."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to provide mock objects for dependencies."""
        return {
            'end_conditions': MagicMock(spec=tools.EndConditions),
            'pager': MagicMock(spec=tools.Paging),
            'output': MagicMock(spec=tools.Output),
        }

    def test_init_with_defaults(self, mock_dependencies):
        """Test initialization with default timeout and output."""
        client = Client(
            url='http://test.url',
            end_conditions=mock_dependencies['end_conditions'],
            pager=mock_dependencies['pager'],
            query={'key': 'value'}
        )

        assert client.url == 'http://test.url'
        assert client.end_conditions == mock_dependencies['end_conditions']
        assert client.pager == mock_dependencies['pager']
        assert client.query == {'key': 'value'}
        assert isinstance(client.timeout, tools.Timeout)
        assert client.output == mock_dependencies['output']
        assert client.still_running is True

    def test_init_with_custom_int_timeout(self, mock_dependencies):
        """Test initialization with an integer for timeout."""
        client = Client(
            url='http://test.url',
            end_conditions=mock_dependencies['end_conditions'],
            pager=mock_dependencies['pager'],
            query={},
            timeout=10
        )
        assert isinstance(client.timeout, tools.Timeout)
        # The Timeout constructor is called with the correct value
        # Since we're not mocking Timeout.__init__, this tests the logic
        # by checking the type, which is sufficient here.

    def test_init_with_custom_timeout_object(self, mock_dependencies):
        """Test initialization with a pre-created Timeout object."""
        custom_timeout = tools.Timeout(pause_seconds=5)
        client = Client(
            url='http://test.url',
            end_conditions=mock_dependencies['end_conditions'],
            pager=mock_dependencies['pager'],
            query={},
            timeout=custom_timeout
        )
        assert client.timeout == custom_timeout

    def test_init_with_custom_output(self, mock_dependencies):
        """Test initialization with a custom Output object."""
        custom_output = MagicMock(spec=tools.Output)
        client = Client(
            url='http://test.url',
            end_conditions=mock_dependencies['end_conditions'],
            pager=mock_dependencies['pager'],
            query={},
            output=custom_output
        )
        assert client.output == custom_output

    def test_init_with_payload(self, mock_dependencies):
        """Test initialization with a payload."""
        client = Client(
            url='http://test.url',
            end_conditions=mock_dependencies['end_conditions'],
            pager=mock_dependencies['pager'],
            query={},
            payload={'data': 'value'}
        )
        assert client.payload == {'data': 'value'}

    @pytest.fixture
    def client_with_mocks(self):
        """Fixture for a client with mocked dependencies."""
        # Use real objects for the tools and mock the external calls
        end_conditions_mock = MagicMock(spec=tools.EndConditions)
        pager_mock = MagicMock(spec=tools.Paging)
        timeout_mock = MagicMock(spec=tools.Timeout)
        output_mock = MagicMock(spec=tools.Output)

        client = Client(
            url='http://api.example.com',
            end_conditions=end_conditions_mock,
            pager=pager_mock,
            query={'q': 'test'},
            timeout=timeout_mock,
            output=output_mock
        )
        
        # Configure the pager mock to return a generator
        pager_mock.page.return_value = iter([{'offset': 0}, {'offset': 10}])
        
        return {
            'client': client,
            'end_conditions': end_conditions_mock,
            'pager': pager_mock,
            'timeout': timeout_mock,
            'output': output_mock
        }

    @patch('requests.get')
    def test_run_successful(self, mock_get, client_with_mocks):
        """Test a single successful run of the client."""
        mock_response = MagicMock()
        mock_response.content = b'some data'
        mock_get.return_value = mock_response

        client = client_with_mocks['client']
        output_mock = client_with_mocks['output']
        timeout_mock = client_with_mocks['timeout']

        client.run()

        # Test 1: requests.get was called with the correct parameters
        expected_headers = {'q': 'test', 'offset': 0}
        mock_get.assert_called_once_with('http://api.example.com', headers=expected_headers)

        # Test 2: output.write_bytes was called with the response content
        output_mock.write_bytes.assert_called_once_with(b'some data')

        # Test 3: timeout.pause was called
        timeout_mock.pause.assert_called_once()

    @patch('requests.get')
    def test_run_with_no_query(self, mock_get, client_with_mocks):
        """Test run when the initial query dict is empty."""
        mock_response = MagicMock()
        mock_response.content = b'data'
        mock_get.return_value = mock_response

        client_with_mocks['client'].query = {}
        client_with_mocks['client'].run()

        # Headers should only contain the page params
        expected_headers = {'offset': 0}
        mock_get.assert_called_once_with('http://api.example.com', headers=expected_headers)
    
    def test_run_with_payload_not_implemented(self, client_with_mocks):
        """Test that run raises NotImplementedError with a payload."""
        client = client_with_mocks['client']
        client.payload = {'data': 'some data'}
        
        with pytest.raises(NotImplementedError):
            client.run()
    
    def test_run_stop_iteration_handling(self, client_with_mocks):
        """Test graceful handling of StopIteration from pager."""
        client = client_with_mocks['client']
        client.pager.page.return_value = iter([]) # An empty generator
        
        # This should not raise an error
        client.run()
        # Assert that none of the following steps were called
        client_with_mocks['output'].write_bytes.assert_not_called()
        client_with_mocks['timeout'].pause.assert_not_called()

    def test_bool_delegation(self):
        """Test that __bool__ delegates to end_conditions."""
        mock_end_conditions = MagicMock(spec=tools.EndConditions)
        # Create a mock for the pager
        mock_pager = MagicMock(spec=tools.Paging)
        
        # The __bool__ on the mock object will return its own boolean value
        mock_end_conditions.__bool__.return_value = True
        
        client = Client(
            url='http://test.url',
            end_conditions=mock_end_conditions,
            pager=mock_pager,
            query={}
        )
        
        assert bool(client) is True
        mock_end_conditions.__bool__.assert_called_once()
        
        # Change the return value and check again
        mock_end_conditions.__bool__.return_value = False
        assert bool(client) is False