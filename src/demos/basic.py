from interval_py import Interval, IO
from interval_py.internal_rpc_schema import DuplexMessage

interval = Interval("alex_dev_kcLjzxNFxmGLf0aKtLVhuckt6sziQJtxFOdtM19tBrMUp5mj")


@interval.action
async def add_a_number(io: IO):
    pass


@interval.action_with_slug("add-two-numbers")
async def add_two_numbers(io: IO):
    pass


interval.listen()


message = DuplexMessage(id="ok", method_name="INITIALIZE_HOST", data=None, kind="CALL")

print(message.json())
