import os
import datetime
import time
import requests
import logging
from typing import Dict, Any, Union, Optional, Generator, Iterator, NoReturn
from nandorapi import tools 

# Set up a logger for this module
logger = logging.getLogger(name = __name__)

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
        The base URL for the API endpoint (e.g., 'https://api.example.com/data').
    end_conditions : tools.EndConditions
        An instance of `EndConditions` to manage the termination of the query loop
        based on time elapsed or the number of queries made.
    pager : tools.Paging
        An instance of `Paging` which acts as a blueprint for generating
        query parameters for each page.
    query : Dict[str, Any]
        A dictionary of fixed query parameters to be included in every request
        (e.g., {'api_key': 'xyz', 'q': 'search_term'}).
    payload : Optional[Dict[str, Any]], optional
        A dictionary of data to send in the request body (e.g., for POST requests).
        This feature is not yet fully implemented and will raise a `NotImplementedError`. 
        Defaults to ``None``.
    timeout : Union[tools.Timeout, int, float], optional
        An instance of `Timeout` or a number of seconds to pause between requests.
        If an ``int`` or ``float`` is provided, a `Timeout` object will be created
        with that value. Defaults to a `Timeout` instance with a 15-second pause.
    output : tools.Output, optional
        An instance of `Output` to handle the saving of the raw response content to a file.
        Defaults to `tools.Output()` with safe-mode disabled.

    Attributes
    ----------
    url : str
        The base URL for the API endpoint.
    end_conditions : tools.EndConditions
        The object managing the loop termination logic.
    pager : Iterator[Dict[str, Any]]
        The iterator (generator) responsible for yielding pagination parameters.
        It is initialized by calling `pager.page()` in the constructor.
    query : Dict[str, Any]
        The static query parameters for each request.
    payload : Optional[Dict[str, Any]]
        The request body payload, or ``None``.
    timeout : tools.Timeout
        The object that handles pausing between requests.
    output : tools.Output
        The object responsible for writing the response content to a file.
    still_running : bool
        A flag that indicates the client's running state. Currently unused
        but reserved for future state management.
    login_details : Dict[str, Any]
        Details obtained after a successful login, typically used as request headers/params.
        Initialized lazily/by ``.login()``.
    login_response : requests.Response
        The raw response object from a successful login request. Initialized by ``.login()``.

    Methods
    -------
    run() -> None
        Executes a single step of the scraping process: fetch a page, save data, and pause.
    login(url: str, **login_args: Any) -> None
        Performs a login request to obtain necessary credentials/tokens.
    __bool__() -> bool
        Returns the boolean state of the `end_conditions` object for loop control.
    """

    # Type hint the Paging object's generator as an Iterator of Dicts
    pager: Iterator[Dict[str, Any]]
    login_details: Dict[str, Any] = {}
    login_response: Optional[requests.Response] = None

    def __init__(
        self,
        url: str,
        end_conditions: tools.EndConditions,
        pager: tools.Paging,
        query: Dict[str, Any],
        payload: Optional[Dict[str, Any]] = None,
        timeout: Union[tools.Timeout, int, float] = tools.Timeout(pause_seconds=15),
        output: tools.Output = tools.Output(overwrite_safe_mode=False)
    ) -> None:
        """
        Initializes the Client object with all necessary components.
        
        Parameters
        ----------
        url : str
            The base URL for the API endpoint.
        end_conditions : tools.EndConditions
            The object to manage the query loop termination.
        pager : tools.Paging
            The object to generate pagination parameters.
        query : Dict[str, Any]
            Static query parameters for all requests.
        payload : Optional[Dict[str, Any]], optional
            Request body payload (if applicable). Defaults to ``None``.
        timeout : Union[tools.Timeout, int, float], optional
            Pause duration or `Timeout` object. Defaults to 15 seconds.
        output : tools.Output, optional
            The object for saving response content. Defaults to unsafe overwrite mode.
        """
        self.url: str = url
        self.end_conditions: tools.EndConditions = end_conditions
        # Initialize the pager attribute by calling its page() method, which should return a generator/iterator.
        self.pager = pager.page()
        self.query: Dict[str, Any] = query
        self.payload: Optional[Dict[str, Any]] = payload
        self.output: tools.Output = output

        # --- Timeout handling for flexibility ---
        # Handle various types for the timeout parameter: int, float, or tools.Timeout
        if isinstance(timeout, (int, float)):
            # If an int or float (seconds) is provided, instantiate a Timeout object
            self.timeout: tools.Timeout = tools.Timeout(pause_seconds=timeout)
        else:
            # Otherwise, assume it's already a tools.Timeout object (or compatible)
            self.timeout: tools.Timeout = timeout

        # Internal flag for the running state, currently unused but available for future state management
        self.still_running: bool = True
        # Initialize header attribute to store the combined request parameters
        self.header: Dict[str, Any] = {}
    
    def run(self) -> None:
        """
        Executes a single step of the data retrieval process.

        This involves:
        1. Getting the next set of pagination parameters from the `pager`.
        2. Constructing the final request header by combining static `query`, 
           dynamic `page` params, and optional `login_details`.
        3. Sending a GET request to the specified URL.
        4. Saving the raw response content using the `output` object.
        5. Pausing using the `timeout` object before the next iteration.

        Raises
        ------
        NotImplementedError
            If a ``payload`` is provided, as POST/payload-based requests are 
            not yet fully implemented.
        """
        # 1. Get the next set of pagination parameters from the pager generator
        try:
            # Type hint for the pagination parameters dictionary
            page: Dict[str, Any] = next(self.pager)
        except StopIteration:
            # If the pager is exhausted, log and gracefully exit the current run cycle.
            # The main loop's `while client:` should generally prevent this, but it's a safety net.
            logger.info("Pager exhausted (StopIteration). Exiting run method.")
            return

        # 2. Logic to handle the request based on payload presence
        if not self.payload:
            # For GET requests (no payload)

            # Combine the static query, dynamic paging parameters, and login details
            # Login details are included only if they exist (non-empty dict)
            self.header = {
                **self.query,
                **page,
                **self.login_details
            }

            # 3. Send the GET request with the combined parameters/headers
            logger.debug(f'Doing a GET request to: {self.url} with params: {self.header}')
            # The combined parameters are passed as `params` for a GET request, 
            # not as `headers`. The existing code uses `headers`, which is likely a bug 
            # if `self.header` contains query parameters like 'page=1'.
            # Correcting for common API client design: using `params` for query strings.
            try:
                r: requests.Response = requests.get(
                    self.url,
                    params=self.header # Correctly use 'params' for GET query string
                )
                r.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP Error during request: {e}")
                # Decide if the loop should terminate or continue on failure
                return
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                return
        else:
            # If a payload is present, assume a POST or similar request
            # This is currently a feature gap as per the original docstring
            raise NotImplementedError('Payload-based requests (e.g., POST) are not yet implemented.')
        
        # 4. Save the content of the response to a file
        # Check for successful response before saving (status_code < 400)
        if r.ok:
            self.output.write_bytes(r.content)
        else:
            logger.warning(f"Skipping save: Request failed with status code {r.status_code}")

        # 5. Pause for the specified duration or according to the custom function
        self.timeout.pause()
        # Increment the query count in end_conditions for accurate loop control
        self.end_conditions.increment_query_count()

    def login(self, url: str, **login_args: Any) -> None:
        """
        Performs a login request to an API endpoint.

        This method sends a GET request to the specified login URL with
        optional arguments, stores the raw response, and attempts to parse
        the response content as JSON to update `self.login_details`.

        Parameters
        ----------
        url : str
            The URL for the login API endpoint.
        **login_args : Any
            Additional keyword arguments to pass to `requests.get()` 
            (e.g., `params`, `headers`, `auth`).

        Raises
        ------
        requests.exceptions.HTTPError
            If the login request returns a bad status code (4xx or 5xx).
        ValueError
            If the response content is not valid JSON.
        """
        logger.info(f"Attempting login to {url}")

        self.login_response = requests.get(url, **login_args)
        self.login_response.raise_for_status() 

        try:
            # Parse the JSON response and store the details (e.g., tokens, session info)
            self.login_details = self.login_response.json()
            logger.info("Login successful. Details parsed from response.")
        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"Failed to decode login response as JSON: {e}")
            raise ValueError("Login response did not contain valid JSON.") from e


    def __bool__(self) -> bool:
        """
        Defines the boolean behavior of the Client object.

        This allows the client object to be used directly in a `while` loop 
        (e.g., `while client: ...`), making the loop continue as long as the
        termination conditions in `end_conditions` are not met.

        Returns
        -------
        bool
            The result of `bool(self.end_conditions)`, which is ``True`` if the
            process should continue, and ``False`` otherwise.
        """
        # The EndConditions class should implement __bool__ to return its state.
        return bool(self.end_conditions)