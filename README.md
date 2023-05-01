<a href="https://interval.com">
  <img alt="Interval" width="100" height="100" style="border-radius: 6px;" src="https://interval.com/img/readme-assets/interval-avatar.png">
</a>

# Interval Python SDK

[![pypi version](https://img.shields.io/pypi/v/interval-sdk?style=flat)](https://pypi.org/project/interval-sdk) [![Documentation](https://img.shields.io/badge/documentation-informational)](https://interval.com/docs) [![Twitter](https://img.shields.io/twitter/follow/useinterval.svg?color=%2338A1F3&label=twitter&style=flat)](https://twitter.com/useinterval) [![Discord](https://img.shields.io/badge/discord-join-blueviolet)](https://interval.com/discord)

[Interval](https://interval.com) lets you quickly build internal web apps (think: customer support tools, admin panels, etc.) just by writing backend Python code.

This is our Python SDK which connects to the interval.com web app. If you don't have an Interval account, you can [create one here](https://interval.com/signup). All core features are free to use.

## Why choose Interval?

_"Python code > no-code"_

Interval is an alternative to no-code/low-code UI builders. Modern frontend development is inherently complicated, and teams rightfully want to spend minimal engineering resources on internal dashboards. No-code tools attempt to solve this problem by allowing you to build UIs in a web browser without writing any frontend code.

We don't think this is the right solution. **Building UIs for mission-critical tools in your web browser** — often by non-technical teammates, outside of your codebase, without versioning or code review — **is an anti-pattern.** Apps built in this manner are brittle and break in unexpected ways.

With Interval, **all of the code for generating your web UIs lives within your app's codebase.** Tools built with Interval (we call these [actions](https://interval.com/docs/concepts/actions)) are just asynchronous functions that run in your backend. Because these are plain old functions, you can access the complete power of your Python app. You can loop, conditionally branch, access shared functions, and so on. When you need to request input or display output, `await` any of our [I/O methods](https://interval.com/docs/io-methods/) to present a form to the user and your script will pause execution until input is received.

Here's a simple app with a single "Hello, world" action:

```python
from interval_sdk import Interval, IO

# Initialize Interval
interval = Interval(api_key="<YOUR API KEY>")

@interval.action
async def hello_world(io: IO):
    name = await io.input.text("Your name")
    return f"Hello, {name}"


# Synchronously listen, blocking forever
interval.listen()
```

To not block, interval can also be run asynchronously using
`interval.listen_async()`. You must provide your own event loop.

The task will complete as soon as connection to Interval completes, so you
likely want to run forever or run alongside another permanent task.

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

Interval:

- Makes creating full-stack apps as easy as writing CLI scripts.
- Can scale from a handful of scripts to robust multi-user dashboards.
- Lets you build faster than no-code, without leaving your codebase & IDE.

With Interval, you do not need to:

- Write REST or GraphQL API endpoints to connect internal functionality to no-code tools.
- Give Interval write access to your database (or give us _any_ of your credentials, for that matter).
- Build web UIs with a drag-and-drop interface.

## More about Interval

- 📖 [Documentation](https://interval.com/docs)
- 🌐 [Interval website](https://interval.com)
- 💬 [Discord community](https://interval.com/discord)
- 📰 [Product updates](https://interval.com/blog)

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
