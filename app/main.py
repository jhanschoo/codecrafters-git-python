import argparse

from git_repository import GitRepository

parser = argparse.ArgumentParser(description="The stupidest content tracker")

subparsers = parser.add_subparsers(dest="command", title="Commands", required=True)
parser_init = subparsers.add_parser("init", help="Initialize a new, empty repository.")
parser_init.add_argument("path", metavar="directory", nargs="?", default=".", help="Where to create the repository.")
parser_init.set_defaults(func=lambda **kwargs: GitRepository.create(kwargs["path"]))

# we disable prefix_chars so that -p can be interpreted as a value of "type". prefix_chars must be nonempty, so we supply `\0` here.
parser_cat_file = subparsers.add_parser("cat-file", prefix_chars='\0', help="Provide content of repository objects")
parser_cat_file.add_argument("type", choices=["blob", "commit", "tag", "tree", "-p"], help="Specify the type")
parser_cat_file.add_argument("object", metavar="object", help="The object to display")
parser_cat_file.set_defaults(func=lambda **kwargs: GitRepository.find().cat_file(kwargs["object"], kwargs["type"]))

parser_hash_object = subparsers.add_parser("hash-object", help="Compute object ID and optionally creates a blob from a file")
parser_hash_object.add_argument("-t", default="blob", choices=["blob", "commit", "tag", "tree"], dest="type", help="Specify the type")
parser_hash_object.add_argument("-w", action="store_true", dest="write", help="Actually write the object into the database")
parser_hash_object.add_argument("path", help="Read object from <file>")
parser_hash_object.add_argument("-p", required=True)
parser_hash_object.set_defaults(func=lambda **kwargs: GitRepository.hash_object(kwargs["path"], kwargs["type"], kwargs["write"]))

def main() -> None:
    args = parser.parse_args()
    args.func(**vars(args))

if __name__ == "__main__":
    main()
