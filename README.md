# interval-sdk

## Installation

Install using pip, (or your python package manager of choice):

```
pip install interval-sdk
```

## API

*Note:* Proper documentation is in progress!

See `src/demos/basic.py` and `src/tests` for a better overview, but in short:

```python
from interval_sdk import Interval, IO

# Initialize Interval
interval = Interval("API_KEY")

# Add an action using the function name as the slug
@interval.action
async def hello_interval():
    return {"hello": "from python!"}

# Add an action using a custom slug (can contain hyphens) and additional configuration
@interval.action(slug='echo-message', unlisted=True)
async def echo_message(io: IO):
    [message] = await io.group(io.input.text("Hello!", help_text="From python!"))

    return {"message": message}


# Synchronously listen, blocking forever
interval.listen()
```

To not block, interval can also be run asynchronously using
`interval.listen_async()`. You must provide your own event loop.

The task will complete as soon as connection to Interval completes, so you
likely want to run forever or run alongside another permanent task.

```python
import asyncio

# This is what synchronous `listen()` does under the hood
loop = asyncio.get_event_loop()
task = loop.create_task(interval.listen_async())
def handle_done(task: asyncio.Task[None]):
    try:
        task.result()
    except:
        loop.stop()

task.add_done_callback(handle_done)
loop.run_forever()
```

If you are using `run_forever()`, you'll probably want to add signal handlers
to close the loop gracefully on process termination:

```python
import asyncio, signal

loop = asyncio.get_event_loop()
task = loop.create_task(interval.listen_async())
def handle_done(task: asyncio.Task[None]):
    try:
        task.result()
    except:
        loop.stop()

task.add_done_callback(handle_done)
for sig in {signal.SIGINT, signal.SIGTERM}:
    loop.add_signal_handler(sig, loop.stop)
loop.run_forever()
```


## Contributing

This project uses [Poetry](https://python-poetry.org/) for dependency
management

1. `poetry install` to install dependencies
2. `poetry shell` to activate the virtual environment

Tasks are configured using [poethepoet](https://github.com/nat-n/poethepoet)
(installed as a dev dependency).

- `poe demo [demo_name]` to run a demo (`basic` by default if `demo_name` omitted)
- `poe test` to run `pytest` (can also run `pytest` directly in virtual env)

Code is formatted using [Black](https://github.com/psf/black). Please configure
your editor to format on save using Black, or run `poe format` to format the
code before committing changes.

## Tests

*Note:* Tests currently require a local instance of the Interval backend.

Tests use [pytest](https://docs.pytest.org/en/7.1.x/) and
[playwright](https://playwright.dev/python/).

Currently assumes the `test-runner@interval.com` user exists already.
Run `yarn test` in the `web` directory at least once to create it before
running these.
