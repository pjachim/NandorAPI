import os
import datetime
import time
from typing import Iterator, Dict, List, Optional, Any, Callable, Union, Tuple, NoReturn


# --- Paging Class ---

class Paging:
    """
    Implements a robust paging mechanism for iterating over data in chunks 
    using either cursor/offset or page number-based pagination.

    This class provides a generator that yields query parameters for each page of data.

    Parameters
    ----------
    cursor_param : str, optional
        The name of the parameter used for the cursor/offset in the query (e.g., 'offset', 'cursor'). 
        Must be provided along with `cursor_value` for cursor mode. Defaults to ``None``.
    cursor_value : int, optional
        The initial value of the cursor/offset. Defaults to ``None``.
    max_results_value : int, optional
        The maximum number of results to retrieve per page (e.g., 'limit', 'count'). 
        Defaults to ``None``.
    max_results_param : str | None, optional
        The name of the parameter used to specify the maximum number of results per page.
        If ``None``, this parameter is not included in the output dictionary. Defaults to ``None``.
    page_param : str, optional
        The name of the parameter used for the page number (e.g., 'page', 'p'). 
        Must be provided along with `page_value` for page mode. Defaults to ``None``.
    page_value : int, optional
        The initial value of the page number. Defaults to ``None``.

    Attributes
    ----------
    state_dict : Dict[str, str]
        Dictionary holding the current fixed paging parameters (like 'limit'). 
        The dynamic cursor/page value is added before yielding. Note: Values are stored as strings 
        to match common HTTP query parameter conventions.
    state_value : int
        The current value of the dynamic parameter (cursor/offset or page number).
    state_param : str
        The name of the dynamic parameter (e.g., 'offset' or 'page').
    max_results_value : Optional[int]
        The maximum number of results per page.
    cursor_mode : bool
        Flag indicating if the client is running in cursor/offset mode.
    page_mode : bool
        Flag indicating if the client is running in page number mode.
    live_query : bool
        A flag that controls the `page` generator. When ``False``, the generator stops yielding.

    Methods
    -------
    page() -> Iterator[Dict[str, str]]
        Yields the current paging parameters for each page until `kill_paging` is called.
    kill_paging() -> None
        Stops the paging process by setting the `live_query` flag to ``False``.
    """
    
    # Type hint for instance attributes that are not immediately defined in __init__
    state_value: int
    state_param: str
    cursor_mode: bool
    page_mode: bool

    def __init__(
        self,
        cursor_param: Optional[str] = None,
        cursor_value: Optional[int] = None,
        max_results_value: Optional[int] = None,
        max_results_param: Optional[str] = None,
        page_param: Optional[str] = None,
        page_value: Optional[int] = None
    ) -> None:
        """
        Initializes the Paging object and determines the pagination mode (cursor or page number).
        
        A `ValueError` is raised if an incomplete or invalid combination of parameters is provided.
        """
        # The dictionary to hold all constant query parameters (like limit/count)
        self.state_dict: Dict[str, str] = {}
        
        # If a max results parameter name is provided, add it to the state dictionary
        if max_results_param is not None and max_results_value is not None:
            # Store the value as a string for use in query parameters
            self.state_dict[max_results_param] = str(max_results_value)

        self.max_results_value: Optional[int] = max_results_value

        # --- Determine Pagination Mode ---

        is_cursor_mode = (cursor_param is not None) and (cursor_value is not None)
        is_page_mode = (page_param is not None) and (page_value is not None)
        
        # Exclusive check: only one mode can be active
        if is_cursor_mode and is_page_mode:
            raise ValueError('Cannot specify both cursor and page parameters. Choose one pagination mode.')

        if is_cursor_mode:
            # Cursor/Offset Mode setup
            self.state_value = cursor_value  # type: ignore[assignment] # Value is checked for None
            self.state_param = cursor_param  # type: ignore[assignment] # Value is checked for None
            self.cursor_mode = True
            self.page_mode = False

        elif is_page_mode:
            # Page Number Mode setup
            self.state_value = page_value  # type: ignore[assignment] # Value is checked for None
            self.state_param = page_param  # type: ignore[assignment] # Value is checked for None
            self.page_mode = True
            self.cursor_mode = False

        else:
            # Neither mode was sufficiently specified
            raise ValueError('Either (cursor_param and cursor_value) OR (page_param and page_value) must be provided.')

        # Flag to control the generator loop's termination
        self.live_query: bool = True

    def page(self) -> Iterator[Dict[str, str]]:
        """
        A generator that yields a dictionary of paginated query parameters.

        The generator runs indefinitely until the `live_query` attribute is set to ``False``
        (typically via the `kill_paging` method). In each iteration, it updates the `state_dict`
        with the current dynamic parameter value and yields the complete set of parameters.

        Yields
        ------
        Dict[str, str]
            A dictionary containing the query parameters for the current page,
            including the dynamic cursor/page number and fixed max results (if specified).
        """
        while self.live_query:
            # Update the state dictionary with the current dynamic value (e.g., 'offset': '0')
            # The dynamic value is converted to a string here for URL compatibility.
            self.state_dict[self.state_param] = str(self.state_value)

            # Yield the complete set of parameters for the current page
            yield self.state_dict

            # Increment the state value based on the active mode
            if self.cursor_mode:
                # In cursor/offset mode, increment by the max_results_value (page size)
                if self.max_results_value is None:
                    # Defensive check if max_results_value is unexpectedly None in cursor mode
                    raise AttributeError('max_results_value cannot be None in cursor_mode for incrementing.')
                self.state_value += self.max_results_value
            elif self.page_mode:
                # In page mode, increment by 1
                self.state_value += 1
            # Note: No action is required if live_query becomes False immediately after yielding.


    def kill_paging(self) -> None:
        """
        Sets the `live_query` attribute to ``False`` to signal the `page` generator to stop.

        This method is the standard way to terminate the pagination loop externally 
        (e.g., by the API client when an empty response is received).
        """
        self.live_query = False


# --- EndConditions Class ---

class EndConditions:
    """
    Manages conditions for stopping a data retrieval process based on the number of queries
    or a time limit.

    This class provides a simple mechanism to check if a process should continue based on
    predefined limits. It is designed to be used as a boolean in a `while` loop to control 
    execution flow.

    Parameters
    ----------
    max_queries : Optional[int], optional
        The maximum number of queries to allow before the process stops.
        ``None`` means no query count limit. Defaults to 1,000.
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
        A counter for the number of successful queries executed. Starts at 0.
    now : Optional[datetime.datetime]
        The current datetime, updated on each state update/check.

    Methods
    -------
    __bool__() -> bool
        Returns ``True`` if the process should continue, ``False`` otherwise, and updates the state.
    increment_query_count() -> None
        Manually increments the query counter. Useful when the `__bool__` check is separate 
        from the query execution.
    """
    
    def __init__(
        self,
        max_queries: Optional[int] = 1_000,
        end_date: datetime.datetime = datetime.datetime.now() + datetime.timedelta(days=1)
    ) -> None:
        """Initializes the EndConditions object with query and time limits."""
        self.max_queries: Optional[int] = max_queries
        self.end_date: datetime.datetime = end_date

        # Counter for queries, starts at 0.
        self.i: int = 0
        self.now: Optional[datetime.datetime] = None
        
        # Store initial time to measure duration if needed later
        self._start_time: datetime.datetime = datetime.datetime.now()

    def increment_query_count(self) -> None:
        """
        Manually increments the internal query counter (`self.i`).

        This method is used by the external client (e.g., `Client.run()`) to log a completed query.
        """
        self.i += 1

    def _update_time(self) -> None:
        """Records the current time for the time-based check."""
        self.now = datetime.datetime.now()

    def _keep_querying(self) -> bool:
        """
        Checks if the predefined conditions for stopping have been met.

        This method is the core logic, checking against `max_queries` and `end_date`.

        Returns
        -------
        bool
            ``True`` if both the query count and time limit are within bounds.
            ``False`` otherwise.
        """
        # Update the current time
        self._update_time()

        # Check 1: Query Count Limit
        # Note: The logic has been changed. The counter `self.i` is now incremented 
        # *after* the request, typically via `increment_query_count`. 
        # The check must be `self.i < self.max_queries` to allow `max_queries` executions.
        if self.max_queries is not None and self.i >= self.max_queries:
            return False
        
        # Check 2: Time Limit
        # The check must ensure 'self.now' is not None before comparison
        if self.now and self.now >= self.end_date:
            return False
        
        # If neither condition is met, continue querying
        return True

    def __bool__(self) -> bool:
        """
        Enables the object to be used in a boolean context (e.g., `while end_conditions_obj: ...`).

        This method encapsulates the check for all termination conditions. Since the `i` counter
        is updated externally, `__bool__` is a pure check method.

        Returns
        -------
        bool
            ``True`` if the process should continue, ``False`` otherwise.
        """
        # The `_keep_querying` method now handles the internal checks.
        return self._keep_querying()


# --- Output Class ---

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
        The format string for the `{date}` placeholder (e.g., '%Y-%m-%d').
        Defaults to '%Y-%m-%d'.
    overwrite_safe_mode : bool, optional
        If ``True``, raises a `FileExistsError` if the destination folder already exists.
        Defaults to ``True``.

    Attributes
    ----------
    date_format : str
        The format for the date placeholder.
    index_length : int
        The padding length for the index.
    overwrite_safe_mode : bool
        Flag to prevent overwriting existing directories.
    i : int
        Internal counter for file indexing, starting at 0.
    path_template : str
        The complete, unformatted path template string (e.g., 'nandor_downloads/{date}/download_{index}.json').
    folder_path_template : str
        The complete, unformatted directory path (e.g., 'nandor_downloads/{date}').

    Methods
    -------
    write_bytes(data: bytes) -> bool
        Writes the given bytes to a new file, incrementing the internal index.
    """
    
    # Type hint for folder_path_template which is created in __init__
    folder_path_template: str

    def __init__(
        self,
        output_name: str = 'download_{index}.json',
        folder_path: List[str] = ['nandor_downloads', '{date}'],
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
        # Store the folder path template separately for easier directory creation
        self.folder_path_template, _ = os.path.split(self.path_template)

        # Create the save location on initialization
        self._make_save_location()

    def _make_save_location(self) -> None:
        """
        Creates the directory for saving files based on the `folder_path_template`.

        Raises
        ------
        FileExistsError
            If `overwrite_safe_mode` is enabled and the directory already exists.
        """
        # Format the folder path (e.g., replaces `{date}`)
        folder: str = self._format_paths(self.folder_path_template, index_increment=False)

        # Check for existence in overwrite safe mode
        if os.path.exists(folder) and self.overwrite_safe_mode:
            raise FileExistsError(f'Path "{folder}" already exists, please disable safe mode or change the folder path.')
        
        # Create the directories recursively. `exist_ok=True` is not used here 
        # because we already checked existence (or don't care if safe mode is off).
        os.makedirs(folder, exist_ok=(not self.overwrite_safe_mode))

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
            ``True`` if the write operation was successful.
        """
        # Get the full, formatted path for the current file
        # The index counter `self.i` is incremented inside `_make_path`
        file_path: str = self._make_path()
        
        try:
            # Use binary write mode 'wb' for raw bytes content
            with open(file_path, 'wb') as f:
                f.write(data)
            return True
        except IOError as e:
            # Handle potential file writing errors (e.g., disk full, permissions)
            print(f"Error writing to file {file_path}: {e}")
            return False

    def _make_path(self) -> str:
        """
        Generates the full, formatted file path for the current index and increments the index.

        Returns
        -------
        str
            The complete, formatted file path.
        """
        # `_format_paths` will handle the replacement of all placeholders and increment the index
        path: str = self._format_paths(self.path_template, index_increment=True)
        return path

    def _format_paths(self, path: str, index_increment: bool) -> str:
        """
        Formats a path string by replacing placeholders like `{date}` and `{index}`.

        Parameters
        ----------
        path : str
            The path string containing one or more placeholders.
        index_increment : bool
            If ``True``, the internal file index `self.i` is incremented after formatting.

        Returns
        -------
        str
            The formatted path string.
        """
        format_options: Dict[str, str] = {}

        # Replace '{date}' placeholder with the current date
        if '{date}' in path:
            format_options['date'] = datetime.datetime.now().strftime(self.date_format)

        # Handle '{index}' placeholder
        if '{index}' in path:
            # Replace '{index}' placeholder with the zero-padded index
            format_options['index'] = str(self.i).zfill(self.index_length)
            
            if index_increment:
                # Increment the counter *after* getting the current index for the path
                self.i += 1
        
        # Apply the formatting
        path = path.format(**format_options)

        return path
    
# --- Timeout Class ---

class Timeout:
    """
    Implements a pausing mechanism for controlling the rate of operations.

    This class provides a way to introduce a delay, either for a fixed number of seconds
    or by calling a custom function. It is useful for respecting rate limits on APIs.

    Parameters
    ----------
    pause_func : Optional[Callable[..., Any]], optional
        A custom function to call for the pause. Defaults to ``None``.
    pause_seconds : Optional[Union[int, float]], optional
        The number of seconds to pause. Defaults to ``None``.
    **pause_kwargs : Any
        Keyword arguments to pass to `pause_func` if it is used.

    Attributes
    ----------
    pause_func : Optional[Callable[..., Any]]
        The custom function for pausing.
    pause_seconds : Optional[Union[int, float]]
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
        pause_seconds: Optional[Union[int, float]] = None,
        **pause_kwargs: Any
    ) -> None:
        """Initializes the Timeout object."""
        # Ensure at least one pause method is specified
        if not (pause_func or pause_seconds):
            raise AttributeError('Either pause_func or pause_seconds must be defined.')
        
        self.pause_func: Optional[Callable[..., Any]] = pause_func
        # Allow float for sub-second precision
        self.pause_seconds: Optional[Union[int, float]] = pause_seconds
        self.pause_kwargs: Dict[str, Any] = pause_kwargs

    def pause(self) -> None:
        """
        Executes the pause logic.

        If `pause_seconds` is defined, it uses `time.sleep`. Otherwise, it calls
        the custom `pause_func` with any provided keyword arguments.
        """
        # Prioritize fixed time pause if specified
        if self.pause_seconds is not None:
            # time.sleep accepts both int and float
            time.sleep(self.pause_seconds)
        # Otherwise, use the custom function
        elif self.pause_func:
            self.pause_func(**self.pause_kwargs)