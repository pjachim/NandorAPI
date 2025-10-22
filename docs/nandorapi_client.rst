.. _client_reference:

=======================
The NandorAPI Client
=======================

.. automodule:: nandorapi.client
   :members:

The `Client` class orchestrates the entire data retrieval process by connecting the pagination logic, loop termination conditions, and file output mechanisms. It handles the core tasks of making paginated HTTP requests and respecting rate limits.

.. autoclass:: nandorapi.client.Client
   :members: run, login
   :show-inheritance:

Basic Usage Example
===================

The client is designed to be used in a simple ``while`` loop, where the loop's continuation is governed by the :ref:`end_conditions_reference`.

.. code-block:: python

   import logging
   from nandorapi.client import Client
   from nandorapi.tools import Paging, EndConditions, Output, Timeout

   # Configure logging to see debug messages
   logging.basicConfig(level=logging.INFO)

   # 1. Define Paging: Start at offset 0, fetch 50 results per page, using 'offset' and 'limit' params.
   pager = Paging(
       cursor_param='offset', 
       cursor_value=0, 
       max_results_value=50, 
       max_results_param='limit'
   )

   # 2. Define End Conditions: Stop after 10 total queries (500 records), or after 1 hour.
   end_conditions = EndConditions(
       max_queries=10, 
       end_date=datetime.datetime.now() + datetime.timedelta(hours=1)
   )

   # 3. Define Output: Save files with zero-padded index in a dated folder, disabling overwrite protection.
   output_handler = Output(
       folder_path=['api_data', '{date}'],
       output_name='page_{index}.json',
       index_length=3,
       overwrite_safe_mode=False 
   )

   # 4. Define Timeout: Pause for 2 seconds between each request.
   rate_limiter = Timeout(pause_seconds=2)

   # 5. Initialize Client
   client = Client(
       url='https://api.example.com/v1/search',
       end_conditions=end_conditions,
       pager=pager,
       query={'api_key': '12345', 'format': 'json'}, # Static parameters
       timeout=rate_limiter,
       output=output_handler
   )

   # 6. Run the Scraper
   print("Starting data retrieval loop...")
   while client:
       # The loop continues as long as bool(client.end_conditions) is True
       try:
           client.run()
           print(f"Query {client.end_conditions.i} complete.")
       except requests.exceptions.HTTPError as e:
           print(f"Stopping due to unrecoverable HTTP error: {e}")
           break
       except NotImplementedError as e:
           print(f"Feature not supported: {e}")
           break

   print("Data retrieval finished based on end conditions.")


Utility Components Reference
============================

The `Client` is built upon four mandatory utility classes, located in the `nandorapi.tools` module (or similar).

.. _paging_reference:

Paging (`tools.Paging`)
-----------------------

Handles the generation and iteration of query parameters for pagination.

.. autoclass:: nandorapi.tools.Paging
   :members: page, kill_paging

**Examples of Paging Configuration:**

1. **Cursor/Offset Paging (e.g., Database Style)**

.. code-block:: python

   # Offset (cursor) starts at 500, page size (limit) is 100
   pager = Paging(
       cursor_param='offset',
       cursor_value=500,
       max_results_value=100,
       max_results_param='limit'
   )
   
   generator = pager.page()
   print(next(generator)) # {'limit': '100', 'offset': '500'}
   print(next(generator)) # {'limit': '100', 'offset': '600'}

2. **Page Number Paging (e.g., API Page 1, Page 2)**

.. code-block:: python

   # Page number starts at 1, page size (count) is 25
   pager = Paging(
       page_param='p',
       page_value=1,
       max_results_value=25,
       max_results_param='count'
   )
   
   generator = pager.page()
   print(next(generator)) # {'count': '25', 'p': '1'}
   print(next(generator)) # {'count': '25', 'p': '2'}


.. _end_conditions_reference:

EndConditions (`tools.EndConditions`)
------------------------------------

Manages the loop termination logic based on query count and time limits. Its primary role is to implement the ``__bool__`` method that controls the ``while client:`` loop.

.. autoclass:: nandorapi.tools.EndConditions
   :members: __bool__, increment_query_count

**Examples of EndConditions Configuration:**

1. **Limit by Query Count Only (Max 50 Queries)**

.. code-block:: python

   ec = EndConditions(max_queries=50, end_date=datetime.datetime.max)
   # Loop will stop when 50 queries have been executed and i reaches 50.

2. **Limit by Time Only (Stop in 30 Minutes)**

.. code-block:: python

   import datetime
   future_time = datetime.datetime.now() + datetime.timedelta(minutes=30)
   ec = EndConditions(max_queries=None, end_date=future_time)
   # max_queries=None ensures the query count never terminates the loop.


.. _output_reference:

Output (`tools.Output`)
-----------------------

Manages file path generation, directory creation, and the process of writing raw response content to disk.

.. autoclass:: nandorapi.tools.Output
   :members: write_bytes

**Examples of Output Configuration:**

1. **Custom Naming and Structure (Hourly Folders, JSON files)**

.. code-block:: python

   output = Output(
       # Save to: /data/2025-10-21-23/record_00001.json
       folder_path=['/data', '{date}'],
       output_name='record_{index}.json',
       date_format='%Y-%m-%d-%H', # Date includes hour
       index_length=5,
       overwrite_safe_mode=True
   )

2. **Unsafe Mode (No Overwrite Protection)**

.. code-block:: python

   # Useful for continuous scraping where you don't mind overwriting a pre-existing folder
   output = Output(overwrite_safe_mode=False)


.. _timeout_reference:

Timeout (`tools.Timeout`)
-------------------------

Provides a flexible mechanism to pause execution, respecting API rate limits.

.. autoclass:: nandorapi.tools.Timeout
   :members: pause

**Examples of Timeout Configuration:**

1. **Fixed 10 Second Pause**

.. code-block:: python

   rate_limiter = Timeout(pause_seconds=10)
   # client.run() calls rate_limiter.pause() which runs time.sleep(10)

2. **Custom Pause Function (e.g., exponential backoff)**

If you define a custom function:

.. code-block:: python
   
   def exponential_backoff(attempt: int) -> None:
       """Pauses for 2^attempt seconds."""
       delay = 2 ** attempt
       time.sleep(delay)
       print(f"Paused for {delay} seconds.")
       
   # Note: The client must manage the 'attempt' count externally or the func must handle it internally.
   rate_limiter = Timeout(pause_func=exponential_backoff, attempt=3)
   # client.run() calls rate_limiter.pause() which calls exponential_backoff(attempt=3)