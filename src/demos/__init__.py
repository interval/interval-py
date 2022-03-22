import importlib
from argparse import ArgumentParser


def run_demo(demo: str):
    importlib.import_module("." + demo, package="demos")


def main():
    parser = ArgumentParser("run_demo")
    parser.add_argument(
        "demo_name",
        help="Filename of the demo without the file extension, relative to demos directory",
        nargs="?",
        default="basic",
    )
    args = parser.parse_args()

    run_demo(args.demo_name)


if __name__ == "__main__":
    main()
