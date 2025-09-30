import os, datetime, time

class Paging:
    """
    Implements a paging mechanism for iterating over data in chunks using cursor-based pagination.
    Parameters
    ----------
    cursor_param : str
        The name of the parameter used for the cursor in the paging query.
    max_results_value : int
        The maximum number of results to retrieve per page.
    cursor_value : int, optional
        The initial value of the cursor (default is 0).
    max_results_param : str | None, optional
        The name of the parameter used to specify the maximum number of results per page (default is None).
    Attributes
    ----------
    state_dict : dict[str, int]
        Dictionary holding the current paging parameters.
    cursor_value : int
        The current value of the cursor.
    cursor_param : str
        The name of the cursor parameter.
    max_results_value : int
        The maximum number of results per page.
    live_query : bool
        Indicates whether paging is active.
    Methods
    -------
    page() -> Iterator[dict[str, int]]
        Yields the current paging parameters for each page until paging is killed.
    kill_paging() -> None
        Stops the paging process.
    Examples
    --------
    >>> pager = Paging(cursor_param="offset", max_results_value=100, max_results_param="limit")
    >>> for params in pager.page():
    ...     print(params)
    ...     if some_condition:
    ...         pager.kill_paging()
    {'limit': 100, 'offset': 0}
    {'limit': 100, 'offset': 100}
    {'limit': 100, 'offset': 200}
    ...
    """
    def __init__(
        self,
        cursor_param: str,
        max_results_value: int,
        cursor_value: int = 0,
        max_results_param: str | None = None
    ):
        self.state_dict = {}

        if max_results_param:
            self.state_dict[max_results_param] = max_results_value
        
        self.cursor_value = cursor_value
        self.cursor_param = cursor_param
        self.max_results_value = max_results_value
        self.live_query = True

    def page(self):
        """
        Generator that yields paginated state dictionaries for live queries.
        Iterates while `self.live_query` is True, updating the cursor parameter in
        `self.state_dict` with the current cursor value, and yields the updated state.
        After each yield, the cursor value is incremented by `self.max_results_value`.
        Yields
        ------
        dict
            The updated state dictionary with the current cursor value.
        Notes
        -----
        - Assumes `self.state_dict`, `self.cursor_param`, `self.cursor_value`, 
          `self.max_results_value`, and `self.live_query` are defined in the class.
        - Intended for use in paginated data retrieval scenarios.
        """
        while self.live_query:
            self.state_dict[self.cursor_param] = self.cursor_value
            
            yield self.state_dict

            self.cursor_value += self.max_results_value

    def kill_paging(self) -> None:
        """
        Sets live_query attribute to False, killing the generator.
        """
        self.live_query = False

class EndConditions:
    def __init__(
            self,
            max_queries: int | None = 1_000,
            end_date: datetime.datetime = datetime.datetime.now() + datetime.timedelta(days=1)
        ):
        self.max_queries = max_queries
        self.end_date = end_date

        self.i = -1 # So first state update makes this 0

    def _update_state(self):
        self.i += 1
        self.now = datetime.datetime.now()

    def _keep_querying(self, query) -> bool:
        self._update_state()

        if self.i >= self.max_queries:
            return False
        
        if self.now >= self.end_date:
            return False
        
        return True

    def __bool__(self) -> bool:
        return self._keep_querying()

class Output:
    def __init__(
        self,
        output_name: str = 'download_{index}.json',
        folder_path: list[str] = ['nandor_downloads', '{date}'],
        index_length: int = 5,
        date_format='%Y-%m-%d',
        overwrite_safe_mode: bool = True
    ) -> None:
        self.date_format = date_format
        self.index_length = index_length
        self.overwrite_safe_mode = overwrite_safe_mode

        self.i = 0

        self.path_template = os.path.join(
            *folder_path, output_name
        )

        self._make_save_location()

    def _make_save_location(self):
        folder, _ = os.path.split(self.path_template)
        folder = self._format_paths(folder)

        if os.path.exists(folder) and self.overwrite_safe_mode:
            raise FileExistsError(f'Path {folder} already exists, please update the folder path and try again.')
        
        os.makedirs(folder)


    def write_bytes(self, bytes) -> bool:
        with open(self._make_path(), 'wb') as f:
            f.write(bytes)

    def _make_path(self) -> str:
        path = self.path_template

        path = self._format_paths(path)

        return path

    def _format_paths(self, path: str) -> str:
        format_options = {}

        if '{date}' in path:
            format_options['date'] = datetime.datetime.now().strftime(self.date_format)

        if '{index}' in path:
            format_options['index'] = str(self.i).zfill(self.index_length)
            self.i += 1
        
        path = path.format(**format_options)

        return path
    
class Timeout:
    def __init__(
        self,
        pause_func = None,
        pause_seconds: int | None = None,
        **pause_kwargs
    ):
        if not (pause_func or pause_seconds):
            raise AttributeError('pause_func or pause_seconds must be defined.')
        
        self.pause_func = pause_func
        self.pause_seconds = pause_seconds
        self.pause_kwargs = pause_kwargs

    def pause(self):
        if self.pause_seconds:
            time.sleep(self.pause_seconds)

        else:
            pause = self.pause_func(**self.pause_kwargs)

