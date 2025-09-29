import os, datetime

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
            no_results_path: list[str] = []
        ):
        self.max_queries = max_queries
        self.no_results_path = no_results_path

        self.current_state
        self.i = 0

    def _update_state(self):
        self.i += 1

    def _conditions_met(self, query) -> bool:
        self._update_state()

        if self.no_results_path:
            if self._no_results_condition(query):
                return True
            
        if self.max_queries:
            return self.i >= self.max_queries

    def _no_results_condition(self, query) -> bool:
        for key in self.no_results_path:
            try:
                query = query.get(key)
            except KeyError:
                pass

        if query:
            return True
        else:
            return False

    def __bool__(self) -> bool:
        return self._conditions_met()

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
            folder_path + [output_name]
        )

        self._make_save_location()

    def _make_save_location(self):
        folder, _ = os.path.split(self.path_template)
        folder = self._date_format(folder)

        if os.path.exists(folder) and self.overwrite_safe_mode:
            raise FileExistsError(f'Path {folder} already exists, please update the folder path and try again.')
        
        os.makedirs(folder)


    def write_bytes(self, bytes) -> bool:
        with open(self._make_path(), 'wb') as f:
            f.write(bytes)

    def _make_path(self) -> str:
        path = self.path_template

        path = self._date_format(path)
        path = self._index_format(path)

        return path

    def _date_format(self, path: str) -> str:
        if '{date}' in path:
            date = datetime.datetime.now().strftime(self.date_format)
            path = path.format(index = self.i)

        return path
    
    def _index_format(self, path: str) -> str:
        if '{index}' in self.path_template:
            formatted_index = str(self.i).zfill(self.index_length)
            path = path.format(index = formatted_index)
            self.i += 1

        return path