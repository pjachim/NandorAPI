.. _tools_reference:

=====================================
Utility Tools Reference (nandorapi.tools) 🛠️
=====================================

The `nandorapi` client is built upon a set of four specialized utility classes, found in the ``nandorapi.tools`` module. These tools handle the core non-HTTP logic: pagination, loop termination, file output, and rate limiting.

---

.. _tools_paging:

Paging (tools.Paging) 🔄
-------------------------

The ``Paging`` class is a highly memory-efficient **generator** that creates the dynamic query parameters needed to traverse a paginated API endpoint. It supports two distinct, mutually exclusive modes: **cursor/offset-based** and **page number-based** pagination.

.. autoclass:: nandorapi.tools.Paging
   :members: page, kill_paging

**Key Features:**

* **Two Modes:** Supports **cursor/offset mode** (increments by page size) or **page number mode** (increments by 1).
* **Dynamic Names:** Allows full control over the names of the parameters, such as `'offset'`, `'cursor'`, `'page'`, `'limit'`, or `'count'`.
* **External Control:** The ``.kill_paging()`` method allows the external client to stop the generator gracefully when no more data is available.

**Examples of Paging:**

1.  **Cursor/Offset Mode (Database Style)**

    Used when the API requires a starting **offset** and a maximum **limit** of results per call. The offset increments by the page size (`max_results_value`).

    .. code-block:: python

       from nandorapi.tools import Paging

       # Start at offset 500, fetch 100 results per page, using 'start_at' and 'results_per_page'.
       offset_pager = Paging(
           cursor_param='start_at',         
           cursor_value=500,               
           max_results_param='results_per_page',
           max_results_value=100           
       )

       generator = offset_pager.page()
       
       print(next(generator))  # {'results_per_page': '100', 'start_at': '500'}
       print(next(generator))  # {'results_per_page': '100', 'start_at': '600'}

2.  **Page Number Mode (Simple Page Index)**

    Used when the API requires a simple **page index** and a page size. The page index increments by $1$.

    .. code-block:: python

       # Start at page 1, fetch 25 results per page.
       page_pager = Paging(
           page_param='p',
           page_value=1,
           max_results_param='page_size',
           max_results_value=25 
       )

       generator = page_pager.page()

       print(next(generator))  # {'page_size': '25', 'p': '1'}
       print(next(generator))  # {'page_size': '25', 'p': '2'}

---

.. _tools_endconditions:

EndConditions (tools.EndConditions) 🛑
--------------------------------------

The ``EndConditions`` class acts as the gatekeeper for the entire data retrieval loop. It implements the :py:meth:`~object.__bool__` method, allowing the object to be used directly in a Python ``while`` loop (e.g., ``while client:``).

.. autoclass:: nandorapi.tools.EndConditions
   :members: __bool__, increment_query_count

**Key Features:**

* **Query Limit:** Stops the process when the number of queries executed (**``self.i``**) reaches or exceeds **``max_queries``**. Set to ``None`` to disable.
* **Time Limit:** Stops the process when the current time exceeds the datetime object provided in **``end_date``**.
* **Pure Check:** The ``__bool__`` method is a **pure check**; the query counter is updated separately using **``.increment_query_count()``** *after* a successful query.

**Examples of EndConditions:**

1.  **Combined Count and Time Limit**

    The loop continues only if *both* conditions are met.

    .. code-block:: python

       import datetime
       from nandorapi.tools import EndConditions

       # Stop after 500 queries OR on midnight of the next day, whichever comes first.
       future_date = datetime.datetime.now().replace(hour=0, minute=0, second=0) + datetime.timedelta(days=1)

       ec_combined = EndConditions(
           max_queries=500, 
           end_date=future_date
       )

       # Check if the loop should continue (True initially)
       print(bool(ec_combined))

       # After a query, the Client calls this:
       ec_combined.increment_query_count() 
       print(ec_combined.i) # 1

2.  **Time Limit Only**

    Disabling the query limit by setting it to ``None`` ensures the process runs only until the time threshold is crossed.

    .. code-block:: python

       # Stop in exactly 2 hours, regardless of how many queries are run.
       stop_time = datetime.datetime.now() + datetime.timedelta(hours=2)

       ec_time_only = EndConditions(max_queries=None, end_date=stop_time)
       # Loop runs until datetime.datetime.now() >= stop_time.

---

.. _tools_output:

Output (tools.Output) 💾
-------------------------

The ``Output`` class manages all local file system operations, including folder creation and saving raw response data. Its templating system ensures that files are uniquely named and logically organized.

.. autoclass:: nandorapi.tools.Output
   :members: write_bytes

**Key Features:**

* **Templating:** Uses the dynamic placeholders **``{date}``** (for folder structure) and **``{index}``** (for filenames) to create unique paths.
* **Zero-Padding:** **``index_length``** controls the zero-padding for the index (e.g., ``5`` yields ``00001``), ensuring files sort correctly.
* **Safe Mode:** **``overwrite_safe_mode=True``** prevents the client from running if the target output folder already exists, safeguarding existing data.
* **Binary Write:** The ``.write_bytes()`` method uses binary write mode (``'wb'``), making it suitable for saving raw API responses (JSON, CSV, images, etc.).

**Examples of Output:**

1.  **Custom Folder Structure with Safe Mode**

    The client will raise a ``FileExistsError`` if the target folder structure already exists.

    .. code-block:: python

       from nandorapi.tools import Output

       # Folder is created as: ./my_dumps/2025_10_21_2230/
       # Files are named: rec-00.json, rec-01.json, etc.
       output_safe = Output(
           folder_path=['my_dumps', '{date}'],
           output_name='rec-{index}.json',
           date_format='%Y_%m_%d_%H%M', # Date format includes minute
           index_length=2,
           overwrite_safe_mode=True
       )

       # First write
       output_safe.write_bytes(b'{"id": 1}') # Saves rec-00.json
       print(output_safe.i) # 1

2.  **Unsafe Mode and Minimal Path**

    Used when you are confident the folder can be overwritten or already exists.

    .. code-block:: python

       # Saves files directly to the current directory: download_0.dat, download_1.dat, etc.
       output_unsafe = Output(
           folder_path=['.'], # Current directory
           output_name='download_{index}.dat',
           index_length=1,
           overwrite_safe_mode=False
       )

---

.. _tools_timeout:

Timeout (tools.Timeout) ⌚
---------------------------

The ``Timeout`` class manages the pauses between requests, which is critical for adhering to API rate limits. It simplifies the choice between a simple fixed delay and complex dynamic pausing logic.

.. autoclass:: nandorapi.tools.Timeout
   :members: pause

**Key Features:**

* **Fixed Delay:** Uses **``pause_seconds``** (supports ``int`` or ``float`` for sub-second precision) to execute a simple ``time.sleep()``.
* **Custom Logic:** If ``pause_seconds`` is ``None``, it calls a user-provided **``pause_func``** for dynamic logic like exponential backoff or reading `Retry-After` headers.
* **Keyword Arguments:** Supports passing arbitrary **``**pause_kwargs``** to the custom function, allowing it to receive context like the attempt counter.

**Examples of Timeout:**

1.  **Fixed Delay (1 second)**

    The simplest way to enforce a basic rate limit.

    .. code-block:: python

       from nandorapi.tools import Timeout

       # Pause for 1.0 second after every request.
       rate_limiter_fixed = Timeout(pause_seconds=1.0)

       # This is called inside the Client loop:
       rate_limiter_fixed.pause() # Runs time.sleep(1.0)

2.  **Custom Exponential Backoff**

    Defining a custom function for more intelligent rate limiting.

    .. code-block:: python

       import time
       from nandorapi.tools import Timeout
       
       def exponential_backoff(attempt: int, max_delay: int = 60) -> None:
           """Pauses for 2^attempt seconds, capped by max_delay."""
           delay = min(2 ** attempt, max_delay)
           print(f"Pausing for {delay} seconds (attempt {attempt}).")
           time.sleep(delay)

       # The 'attempt' value would be dynamically updated by the Client on retry/fail.
       backoff_limiter = Timeout(
           pause_func=exponential_backoff,
           attempt=3,          # Initial attempt value
           max_delay=30        # Kwarg passed to the custom function
       )

       # If called now, it pauses for min(2^3, 30) = 8 seconds.
       backoff_limiter.pause()