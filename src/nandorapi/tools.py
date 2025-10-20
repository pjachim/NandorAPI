import os
import datetime
import time
from typing import Iterator, Dict, List, Optional, Any, Callable


class Paging:
    """
    Implements a paging mechanism for iterating over data in chunks using cursor-based pagination.

    This class provides a generator that yields query parameters for each page of data,
    making it suitable for APIs or databases that support cursor-based pagination.

    Parameters
    ----------
    cursor_param : str
        The name of the parameter used for the cursor in the paging query (e.g., 'offset', 'cursor').
    max_results_value : int
        The maximum number of results to retrieve per page (e.g., 'limit', 'count').
    cursor_value : int, optional
        The initial value of the cursor. Defaults to 0.
    max_results_param : str | None, optional
        The name of the parameter used to specify the maximum number of results per page.
        If `None`, this parameter is not included in the output dictionary. Defaults to `None`.

    Attributes
    ----------
    state_dict : Dict[str, int]
        Dictionary holding the current paging parameters. This dictionary is updated and yielded
        by the `page` generator.
    cursor_value : int
        The current value of the cursor, which is incremented after each page is yielded.
    cursor_param : str
        The name of the cursor parameter (e.g., 'offset').
    max_results_value : int
        The maximum number of results per page (e.g., 100).
    live_query : bool
        A flag that controls the `page` generator. When `False`, the generator stops yielding.

    Methods
    -------
    page() -> Iterator[Dict[str, int]]
        Yields the current paging parameters for each page until `kill_paging` is called.
    kill_paging() -> None
        Stops the paging process by setting the `live_query` flag to `False`.

    Examples
    --------
    >>> pager = Paging(cursor_param="offset", max_results_value=100, max_results_param="limit")
    >>> for params in pager.page():
    ...     print(params)
    ...     # Assuming data is retrieved and processed here
    ...     if params['offset'] >= 300:
    ...         pager.kill_paging()
    {'limit': 100, 'offset': 0}
    {'limit': 100, 'offset': 100}
    {'limit': 100, 'offset': 200}
    {'limit': 100, 'offset': 300}
    """
    def __init__(
        self,
        cursor_param: str = None,
        cursor_value: int = None,
        max_results_value: int = None,
        max_results_param: Optional[str] = None,
        page_param: str = None,
        page_value: int = None
    ) -> None:
        """
        Initializes the Paging object with parameters for cursor-based pagination.
        """
        self.state_dict: Dict[str, int] = {}

        # If a max results parameter name is provided, add it to the state dictionary
        if max_results_param is not None:
            self.state_dict[max_results_param] = str(max_results_value)

        self.max_results_value: int = max_results_value

        if (cursor_param is not None) and (cursor_value is not None):
            self.cursor_value: int = cursor_value
            self.cursor_param: str = cursor_param
            self.cursor_mode = True
            self.page_mode = False

        elif (page_param is not None) and (page_value is not None):
            self.page_value: int = page_value
            self.page_param: str = page_param
            self.page_mode = True
            self.cursor_mode = False

        else:
            raise ValueError('Either cursor_value and cursor_param or page_value and page_param must be provided.')

        # Flag to control the generator loop
        self.live_query: bool = True

    def page(self) -> Iterator[Dict[str, int]]:
        """
        A generator that yields a dictionary of paginated query parameters.

        The generator runs indefinitely until the `live_query` attribute is set to `False`
        (typically via the `kill_paging` method). In each iteration, it updates the `state_dict`
        with the current cursor value and yields it. The cursor value is then incremented
        by the `max_results_value` for the next page.

        Yields
        ------
        Dict[str, int]
            A dictionary containing the query parameters for the current page,
            including the cursor and max results (if specified).
        """
        if self.cursor_mode:
            self._cursor_paging()

        elif self.page_mode:
            self._page_paging()

    def _cursor_paging(self):
        while self.live_query:
            # Update the state dictionary with the current cursor value
            self.state_dict[self.cursor_param] = str(self.cursor_value)

            yield self.state_dict

            # Increment the cursor for the next page
            self.cursor_value += self.max_results_value


    def _page_paging(self):
        while self.live_query:
            # Update the state dictionary with the current page value
            self.state_dict[self.page_param] = str(self.page_value)

            yield self.state_dict

            # Increment for the next page
            self.page_value += 1


    def kill_paging(self) -> None:
        """
        Sets the `live_query` attribute to `False` to stop the `page` generator.

        This method should be called externally when the pagination loop needs to be terminated,
        for example, when no more data is available from an API.
        """
        self.live_query = False


class EndConditions:
    """
    Manages conditions for stopping a data retrieval process based on the number of queries
    or a time limit.

    This class provides a simple mechanism to check if a process should continue based on
    predefined limits. It can be used as a boolean in a `while` loop to control execution.

    Parameters
    ----------
    max_queries : Optional[int], optional
        The maximum number of queries to allow before the process stops.
        Defaults to 1,000. `None` means no limit.
    end_date : datetime.datetime, optional
        The specific date and time when the process should stop.
        Defaults to 24 hours from the current time.

    Attributes
    ----------
    max_queries : Optional[int]
        The maximum number of queries to execute.
    end_date : datetime.datetime
        The specific datetime object representing the end time.
    i : int
        A counter for the number of queries executed. It starts at -1 so the first update
        makes it 0.
    now : datetime.datetime
        The current datetime, updated on each check.

    Methods
    -------
    __bool__() -> bool
        Returns `True` if the process should continue, `False` otherwise.
    """
    def __init__(
        self,
        max_queries: Optional[int] = 1_000,
        end_date: datetime.datetime = datetime.datetime.now() + datetime.timedelta(days=1)
    ) -> None:
        """Initializes the EndConditions object with query and time limits."""
        self.max_queries: Optional[int] = max_queries
        self.end_date: datetime.datetime = end_date

        # Counter for queries, initialized to -1 for correct zero-based indexing on first call
        self.i: int = -1 
        self.now: Optional[datetime.datetime] = None

    def _update_state(self) -> None:
        """
        Updates the internal state by incrementing the query counter and
        recording the current time.
        """
        self.i += 1
        self.now = datetime.datetime.now()

    def _keep_querying(self) -> bool:
        """
        Checks if the predefined conditions for stopping have been met.

        This method should be used internally by the `__bool__` method. It first
        updates the internal state and then checks against the `max_queries` and
        `end_date`.

        Returns
        -------
        bool
            `True` if both the query count and time limit are within bounds.
            `False` if either the `max_queries` limit has been reached or the
            current time is past the `end_date`.
        """
        # Update the query counter and current time
        self._update_state()

        # Check if the maximum number of queries has been reached
        if self.max_queries is not None and self.i >= self.max_queries:
            return False
        
        # Check if the current time has exceeded the end date
        if self.now and self.now >= self.end_date:
            return False
        
        # If neither condition is met, continue querying
        return True

    def __bool__(self) -> bool:
        """
        Enables the object to be used in a boolean context (e.g., `while end_conditions_obj: ...`).

        Returns
        -------
        bool
            `True` if the process should continue, `False` otherwise.
        """
        return self._keep_querying()


class Output:
    """
    Handles the creation of output file paths and writing of data to disk.

    This class manages file naming, directory creation, and writing of data,
    including support for date and index-based naming conventions.

    Parameters
    ----------
    output_name : str, optional
        The template for the output filename. Can include `{index}` and `{date}` placeholders.
        Defaults to 'download_{index}.json'.
    folder_path : List[str], optional
        A list of directory names to form the path. Can include `{date}`.
        Defaults to `['nandor_downloads', '{date}']`.
    index_length : int, optional
        The number of digits to use for zero-padding the index. Defaults to 5.
    date_format : str, optional
        The format string for the `{date}` placeholder. Defaults to '%Y-%m-%d'.
    overwrite_safe_mode : bool, optional
        If `True`, raises a `FileExistsError` if the destination folder already exists.
        Defaults to `True`.

    Attributes
    ----------
    date_format : str
        The format for the date placeholder.
    index_length : int
        The padding length for the index.
    overwrite_safe_mode : bool
        Flag to prevent overwriting existing directories.
    i : int
        Internal counter for file indexing.
    path_template : str
        The complete, unformatted path template string.

    Methods
    -------
    write_bytes(bytes) -> bool
        Writes the given bytes to a new file, incrementing the internal index.
    """
    def __init__(
        self,
        output_name: str = 'download_{index}.json',
        folder_path: list[str] = ['nandor_downloads', '{date}'],
        index_length: int = 5,
        date_format: str = '%Y-%m-%d',
        overwrite_safe_mode: bool = True
    ) -> None:
        """Initializes the Output object with path and file naming settings."""
        self.date_format: str = date_format
        self.index_length: int = index_length
        self.overwrite_safe_mode: bool = overwrite_safe_mode

        # Internal index counter
        self.i: int = 0

        # Construct the full path template
        self.path_template: str = os.path.join(*folder_path, output_name)

        # Create the save location on initialization
        self._make_save_location()

    def _make_save_location(self) -> None:
        """
        Creates the directory for saving files based on the `path_template`.

        Raises a `FileExistsError` if `overwrite_safe_mode` is enabled and the directory
        already exists.
        """
        # Extract the folder path from the full path template
        folder, _ = os.path.split(self.path_template)
        # Format the folder path (e.g., replaces `{date}`)
        folder = self._format_paths(folder)

        # Check for existence in overwrite safe mode
        if os.path.exists(folder) and self.overwrite_safe_mode:
            raise FileExistsError(f'Path {folder} already exists, please update the folder path and try again.')
        
        # Create the directories. `exist_ok=True` is not used to allow the safe mode check to work.
        os.makedirs(folder, exist_ok=True)

    def write_bytes(self, data: bytes) -> bool:
        """
        Writes a byte string to a new file at the next available index.

        Parameters
        ----------
        data : bytes
            The byte string content to write to the file.

        Returns
        -------
        bool
            `True` if the write operation was successful.
        """
        # Get the full, formatted path for the current file
        file_path: str = self._make_path()
        with open(file_path, 'wb') as f:
            f.write(data)
        return True

    def _make_path(self) -> str:
        """
        Generates the full, formatted file path for the current index.

        This internal method is called before each write to create a unique path.

        Returns
        -------
        str
            The complete, formatted file path.
        """
        path: str = self.path_template
        path = self._format_paths(path)
        return path

    def _format_paths(self, path: str) -> str:
        """
        Formats a path string by replacing placeholders like `{date}` and `{index}`.

        Parameters
        ----------
        path : str
            The path string containing one or more placeholders.

        Returns
        -------
        str
            The formatted path string.
        """
        format_options: Dict[str, str] = {}

        # Replace '{date}' placeholder with the current date
        if '{date}' in path:
            format_options['date'] = datetime.datetime.now().strftime(self.date_format)

        # Replace '{index}' placeholder with the zero-padded index and increment the counter
        if '{index}' in path:
            format_options['index'] = str(self.i).zfill(self.index_length)
            self.i += 1
        
        # Apply the formatting
        path = path.format(**format_options)

        return path
    
class Timeout:
    """
    Implements a pausing mechanism for controlling the rate of operations.

    This class provides a way to introduce a delay, either for a fixed number of seconds
    or by calling a custom function. It is useful for respecting rate limits on APIs.

    Parameters
    ----------
    pause_func : Optional[Callable[..., Any]], optional
        A custom function to call for the pause. Defaults to `None`.
    pause_seconds : Optional[int], optional
        The number of seconds to pause. Defaults to `None`.
    **pause_kwargs : Any
        Keyword arguments to pass to `pause_func` if it is used.

    Attributes
    ----------
    pause_func : Optional[Callable[..., Any]]
        The custom function for pausing.
    pause_seconds : Optional[int]
        The duration of the pause in seconds.
    pause_kwargs : Dict[str, Any]
        Keyword arguments for the custom pause function.

    Methods
    -------
    pause() -> None
        Executes the pause, either using `time.sleep` or by calling the custom function.
    
    Raises
    ------
    AttributeError
        If neither `pause_func` nor `pause_seconds` is provided during initialization.
    """
    def __init__(
        self,
        pause_func: Optional[Callable[..., Any]] = None,
        pause_seconds: Optional[int] = None,
        **pause_kwargs: Any
    ) -> None:
        """Initializes the Timeout object."""
        # Ensure at least one pause method is specified
        if not (pause_func or pause_seconds):
            raise AttributeError('Either pause_func or pause_seconds must be defined.')
        
        self.pause_func: Optional[Callable[..., Any]] = pause_func
        self.pause_seconds: Optional[int] = pause_seconds
        self.pause_kwargs: Dict[str, Any] = pause_kwargs

    def pause(self) -> None:
        """
        Executes the pause.

        If `pause_seconds` is defined, it uses `time.sleep`. Otherwise, it calls
        the custom `pause_func` with any provided keyword arguments.
        """
        # Prioritize fixed time pause if specified
        if self.pause_seconds is not None:
            time.sleep(self.pause_seconds)
        # Otherwise, use the custom function
        elif self.pause_func:
            self.pause_func(**self.pause_kwargs)