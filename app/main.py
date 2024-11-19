import argparse
import zlib
import os

def init(**_kwargs) -> None:
    os.mkdir(".git")
    os.mkdir(".git/objects")
    os.mkdir(".git/refs")
    with open(".git/HEAD", "w") as f:
        f.write("ref: refs/heads/main\n")
    print("Initialized git directory")

def cat_file(p : str, **_kwargs) -> None:
    prefix, rest = p[:2], p[2:]
    with open(os.path.join(".git", "objects", prefix, rest), "rb") as f:
        raw = zlib.decompress(f.read())
        content = raw.decode()
        metadata, content = content.split("\0", 1)
        print(content, end="")

parser = argparse.ArgumentParser()

subparsers = parser.add_subparsers(dest="command", title="subcommands", required=True)
parser_init = subparsers.add_parser("init")
parser_init.set_defaults(func=init)

parser_cat_file = subparsers.add_parser("cat-file")
parser_cat_file.set_defaults(func=cat_file)
parser_cat_file.add_argument("-p", required=True)

def main() -> None:
    args = parser.parse_args()
    args.func(**vars(args))

if __name__ == "__main__":
    main()
