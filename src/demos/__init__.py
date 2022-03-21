import importlib


def run_demo(demo: str):
    importlib.import_module("." + demo, package="demos")
