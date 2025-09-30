import os
import datetime
import time
import requests
from typing import Dict, Any, Union, Optional
from nandorapi import tools


class Client:
    """
    A client for making paginated requests to a REST API.

    This class orchestrates a data retrieval process by combining a `Paging`
    object for pagination, `EndConditions` for loop control, and an `Output`
    object for saving data. It handles the core logic of making HTTP requests,
    pausing between requests, and managing the overall state of the scraper.

    Parameters
    ----------
    url : str
        The base URL for the API endpoint.
    end_conditions : tools.EndConditions
        An instance of `EndConditions` to manage the termination of the query loop
        based on time or query count.
    pager : tools.Paging
        An instance of `Paging` to generate the query parameters for each page.
    query : Dict[str, Any]
        A dictionary of fixed query parameters to be included in every request
        (e.g., {'q': 'search_term'}).
    payload : Optional[Dict[str, Any]], optional
        A dictionary of data to send in the request body (e.g., for POST requests).
        This feature is not yet implemented. Defaults to `None`.
    timeout : Union[tools.Timeout, int, float], optional
        An instance of `Timeout` or a number of seconds to pause between requests.
        If an `int` or `float` is provided, a `Timeout` object will be created
        with that value. Defaults to `Timeout(pause_seconds=15)`.
    output : tools.Output, optional
        An instance of `Output` to handle the saving of the response content to a file.
        Defaults to `tools.Output()`.

    Attributes
    ----------
    url : str
        The base URL for the API endpoint.
    end_conditions : tools.EndConditions
        The object managing the loop termination.
    pager : tools.Paging
        The object responsible for generating pagination parameters.
    query : Dict[str, Any]
        The static query parameters for each request.
    payload : Optional[Dict[str, Any]]
        The request body payload.
    timeout : tools.Timeout
        The object that handles pausing between requests.
    still_running : bool
        A flag that indicates the client's running state.
    
    Methods
    -------
    run() -> None
        Executes a single step of the scraping process, including fetching a page,
        saving the data, and pausing.
    __bool__() -> bool
        Returns the boolean state of the `end_conditions` object, allowing the
        client to be used in a `while` loop.

    Examples
    --------
    >>> # Assuming end_conditions, pager, and output objects are defined
    >>> client = Client(
    ...     url='https://api.example.com/data',
    ...     end_conditions=EndConditions(max_queries=5),
    ...     pager=Paging(cursor_param='page', max_results_value=10),
    ...     query={'category': 'tech'},
    ...     timeout=1
    ... )
    >>> while client:
    ...     client.run()
    # The loop will run for 5 iterations, making a request for each page.
    """

    def __init__(
        self,
        url: str,
        end_conditions: tools.EndConditions,
        pager: tools.Paging,
        query: Dict[str, Any],
        payload: Optional[Dict[str, Any]] = None,
        timeout: Union[tools.Timeout, int, float] = tools.Timeout(pause_seconds=15),
        output: tools.Output = tools.Output()
    ) -> None:
        """Initializes the Client object with all necessary components."""
        self.url: str = url
        self.end_conditions: tools.EndConditions = end_conditions
        self.pager: tools.Paging = pager
        self.query: Dict[str, Any] = query
        self.payload: Optional[Dict[str, Any]] = payload
        self.output: tools.Output = output

        # Handle various types for the timeout parameter
        if isinstance(timeout, (int, float)):
            # If an int or float is provided, create a Timeout object
            self.timeout: tools.Timeout = tools.Timeout(pause_seconds=timeout)
        else:
            # Otherwise, assume it's already a Timeout object
            self.timeout: tools.Timeout = timeout

        # Internal flag for the running state, currently unused but kept for potential future use
        self.still_running: bool = True
    
    def run(self) -> None:
        """
        Executes a single step of the data retrieval process.

        This method gets the next page's parameters from the pager, constructs
        the request header, sends a GET request to the specified URL, writes the
        response content to a file, and then pauses using the timeout object.
        """
        # Get the next set of pagination parameters from the pager generator
        try:
            page: Dict[str, Any] = next(self.pager.page())
        except StopIteration:
            # If the pager is exhausted, nothing to do. The `__bool__` check
            # should prevent this, but it's good practice to handle it.
            return

        if not self.payload:
            # Combine the static query with the dynamic paging parameters
            header: Dict[str, Any] = {
                **self.query,
                **page
            }

            # Send the GET request with the combined parameters
            r: requests.Response = requests.get(
                self.url,
                headers=header
            )
        else:
            # The logic for handling POST requests with a payload would go here
            raise NotImplementedError('Payload-based requests are not yet implemented.')
        
        # Save the content of the response to a file
        self.output.write_bytes(r.content)
        # Pause for the specified duration or according to the custom function
        self.timeout.pause()

    def __bool__(self) -> bool:
        """
        Defines the boolean behavior of the Client object.

        This allows the client to be used directly in a `while` loop (e.g.,
        `while client: ...`), which will continue as long as the
        `end_conditions` are met.

        Returns
        -------
        bool
            The result of `bool(self.end_conditions)`, which is `True` if the
            process should continue, and `False` otherwise.
        """
        return bool(self.end_conditions)