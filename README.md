# NandorAPI: Relentless API Client for Python

NandorAPI is a lightweight and powerful Python library designed to simplify the process of building API clients. By providing core components for common tasks like **pagination**, **rate limiting**, **output management**, and **loop control**, NandorAPI allows you to quickly assemble a robust and reliable client for nearly any HTTP API.

Whether you're scraping data, interacting with a private API, or building a one-off data pipeline, NandorAPI provides the boilerplate you need so you can focus on what matters: the data.

-----

## Why Use NandorAPI?

Traditional API clients often require you to write the same repetitive code for each project:

  - **Pagination:** Manually managing cursors, offsets, or page numbers.
  - **Rate Limiting:** Adding `time.sleep()` calls and managing timeouts to avoid exceeding API limits.
  - **Loop Control:** Implementing custom logic to stop a script after a certain number of requests or a specific time.
  - **Output Handling:** Writing code to create directories and save data to files with dynamic names.

NandorAPI abstracts all of this into simple, reusable classes. You just configure each component, plug them into the `Client` object, and let it handle the rest.

-----

## Key Features

  - **Modular Design:** Each core function (paging, timeouts, end conditions, output) is a separate class, allowing you to mix and match components to fit your specific needs.
  - **Cursor-Based Pagination:** The `Paging` class provides a generator that handles cursor increments automatically, perfect for APIs with `offset` or `page` parameters.
  - **Flexible Loop Control:** The `EndConditions` class lets you set clear stopping points for your client based on a maximum number of queries or a specific date and time.
  - **Dynamic File Management:** The `Output` class automatically creates directories and saves responses to files with dynamic, zero-padded indexes and date-based paths.
  - **Built-in Rate Limiting:** The `Timeout` class handles pauses between requests, either for a fixed duration or by calling a custom function for more complex logic.
  - **Simplified Orchestration:** The `Client` class is the central hub, bringing all the components together. You can run your entire data retrieval process with a single, clear `while client: client.run()` loop.

-----

## Installation

NandorAPI is not currently available on PyPI, so you will need to install it directly from the source code.

```bash
git clone https://github.com/your-repo/NandorAPI.git
cd NandorAPI
pip install -e .
```

-----

## Getting Started

Here's how to build a complete API client in just a few lines of code.

### 1\. Define the Components

First, you'll need to instantiate the building blocks for your client.

```python
import os
from nandorapi import tools
import datetime
from my_custom_logic import dynamic_timeout_func

# 1. Define loop termination rules
end_conditions = tools.EndConditions(
    max_queries=1_000,
    end_date=datetime.datetime.now() + datetime.timedelta(hours=24)
)

# 2. Configure a pager for pagination
pager = tools.Paging(
    cursor_param="offset",
    max_results_value=100,
    max_results_param="limit"
)

# 3. Set up the output file path and naming
output = tools.Output(
    output_name="data_page_{index}.json",
    folder_path=["my_downloads", "{date}"],
    index_length=4
)

# 4. (Optional) Create a timeout object
# You can use a fixed delay...
fixed_timeout = tools.Timeout(pause_seconds=5)
# ...or use a custom function for dynamic rate limiting.
dynamic_timeout = tools.Timeout(pause_func=dynamic_timeout_func)
```

### 2\. Assemble and Run the Client

Now, plug your components into the `Client` object and start your data retrieval loop.

```python
from nandorapi.client import Client

# Define the core request parameters
api_url = "https://api.example.com/v1/search"
static_query = {"query": "python library"}

# Instantiate the client with your components
client = Client(
    url=api_url,
    end_conditions=end_conditions,
    pager=pager,
    query=static_query,
    timeout=fixed_timeout, # Use your chosen timeout object
    output=output
)

# The magic happens here!
print("Starting data retrieval...")
while client:
    # This single call handles all the core logic:
    # 1. Gets the next page parameters from the `pager`.
    # 2. Makes the HTTP request.
    # 3. Saves the response using the `output` object.
    # 4. Pauses using the `timeout` object.
    client.run()

print("Data retrieval complete.")
```

-----

## Contributing

NandorAPI is an open-source project, and contributions are welcome\! If you have an idea for a new feature, a bug report, or a code improvement, please feel free to open an issue or a pull request on the GitHub repository.