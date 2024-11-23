import configparser
import os
import sys
import zlib
from typing import Self, BinaryIO

from git_object import GitObject, GitBlob #GitCommit, GitTree, GitTag, GitBlob

class GitRepository:
    """A DDD entity representing a Git repository."""

    worktree : str
    gitdir : str
    conf : configparser.ConfigParser

    def __init__(self, path: str, force=False):
        """Initialize a new `GitRepository` object representing the repository at `path`.
        The repository system files are expected to reside at `join(path, ".git")`, unless
        `force=True`."""
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

        if not (force or os.path.isdir(self.gitdir)):
            raise Exception(f"Not a Git repository: {path}")
        
        # Read configuration file in .git/config
        self.conf = configparser.ConfigParser()
        cf = self.path_file("config")

        if cf and os.path.exists(cf):
            self.conf.read([cf])
        elif not force:
            raise Exception("Configuration file missing")

        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0:
                raise Exception(f"Unsupported repositoryformatversion {vers}")

    @classmethod
    def create(cls, path: str) -> Self:
        """Create a new repository at `path`."""

        repo = GitRepository(path, force=True)

        # First, we make sure the path either doesn't exist or is an
        # empty dir.

        if os.path.exists(repo.worktree):
            if not os.path.isdir(repo.worktree):
                raise Exception (f"{path} is not a directory!")
            if os.path.exists(repo.gitdir) and os.listdir(repo.gitdir):
                raise Exception(f"{path} is not empty!")
        else:
            os.makedirs(repo.worktree)

        assert repo.path_dir("branches", mkdir=True)
        assert repo.path_dir("objects", mkdir=True)
        assert repo.path_dir("refs", "tags", mkdir=True)
        assert repo.path_dir("refs", "heads", mkdir=True)

        # .git/description
        with open(repo.path_file("description"), "w") as f:
            f.write("Unnamed repository; edit this file 'description' to name the repository.\n")

        # .git/HEAD
        with open(repo.path_file("HEAD"), "w") as f:
            f.write("ref: refs/heads/master\n")

        with open(repo.path_file("config"), "w") as f:
            repo.set_default_core_config()
            repo.config_write(f)

        return repo

    @classmethod
    def find(cls, path=".", required=True) -> Self | None:
        """Find the deepest path prefix of `path` that is a git repository, as identified by having
        a `.git` subdir, and return it as a `GitRepository`."""
        path = os.path.realpath(path)

        if os.path.isdir(os.path.join(path, ".git")):
            return GitRepository(path)

        # If we haven't returned, recurse in parent, if w
        parent = os.path.realpath(os.path.join(path, ".."))

        if parent == path:
            # Bottom case
            # os.path.join("/", "..") == "/":
            # If parent==path, then path is root.
            if required:
                raise Exception("No git directory.")
            else:
                return None

        # Recursive case
        return GitRepository.find(parent, required)

    def path(self, *path: str) -> str:
        """Give `*path` relative to repo's gitdir."""
        return os.path.join(self.gitdir, *path)
    
    def path_file(self, *path: str, mkdir=False) -> str:
        """Give `*path` relative to repo's gitdir, but create dirname(*path[:-1]) if absent,
        and `mkdir=True`.
        For example, `path_file("refs", "remotes", "origin", "HEAD")` will return
        `.git/refs/remotes/origin.` The path returned is itself not guaranteed to refer to an
        existing file."""

        if self.path_dir(*path[:-1], mkdir=mkdir):
            return self.path(*path)
        
    def path_dir(self, *path: str, mkdir=False) -> str | None:
        """Give `*path` relative to repo's gitdir, but validates that path is a directory, performing
        mkdir `*path` if absent and `mkdir=True`."""

        path: str = self.path(*path)

        if os.path.exists(path):
            if os.path.isdir(path):
                return path
            else:
                raise Exception(f"Not a directory: {path}")

        if mkdir:
            os.makedirs(path)
            return path
        else:
            return None

    def object_read(self, sha: str) -> GitObject | None:
        """Read object `sha`. Return a
        GitObject whose exact type depends on the object."""

        path = self.path_file("objects", sha[0:2], sha[2:])

        if not os.path.isfile(path):
            return None

        with open (path, "rb") as f:
            # Note: `decompressobj()` is safer with respect to memory usage, but
            # it would be harder to write correctly.
            raw = zlib.decompress(f.read())

            # Read object type
            x = raw.find(b' ')
            fmt = raw[0:x]

            # Read and validate object size
            y = raw.find(b'\x00', x)
            size = int(raw[x:y].decode("ascii"))
            if size != len(raw) - y - 1:
                raise Exception(f"Malformed object {sha}: bad length")

            # Pick constructor
            match fmt:
                # case b'commit':
                #     return GitCommit(raw[y+1:])
                # case b'tree':
                #     return GitTree(raw[y+1:])
                # case b'tag':
                #     return GitTag(raw[y+1:])
                case b'blob':
                    return GitBlob(raw[y+1:])
                case _:
                    raise Exception(f"Unknown type {fmt.decode("ascii")} for object {sha}")

    def object_write(self, obj: GitObject) -> None:
        """Write object `obj`."""
        result, sha = obj.serialize(self)

        #todo: gate under repo
        # Compute path
        path=self.path_file("objects", sha[0:2], sha[2:], mkdir=True)

        if not os.path.exists(path):
            with open(path, 'wb') as f:
                # Compress and write
                f.write(zlib.compress(result))

    def object_find(self, name: str, fmt=None, follow=None):
        match name:
            case "-p":
                return "blob"
            case _:
                return name

    @staticmethod
    def object_from_data(fd: BinaryIO, fmt: bytes) -> GitObject:
        """deserialize the data in `fd`"""
        data = fd.read()

        match fmt:
            # case b'commit':
            #     return GitCommit(data)
            # case b'tree':
            #     return GitTree(data)
            # case b'tag':
            #     return GitTag(data)
            case b'blob':
                return GitBlob(data)
            case _:
                raise Exception(f"Unknown type {str(fmt)}!")

    def set_default_core_config(self) -> None:
        """Set in `self.conf` k-v pairs that are expected of a just-initialized repository"""
        self.conf["core"] = {
            "repositoryformatversion": "0",
            "filemode": "false",
            "bare": "false",
        }

    def config_write(self, f):
        """Persist `self.conf` to `f`"""
        self.conf.write(f)

    # the following functions primarily do processing to interface with the cli
    def cat_file(self, name: str, fmt: str | None=None) -> None:
        obj = self.object_read(self.object_find(name, fmt=fmt))
        sys.stdout.buffer.write(obj.serialize_data(self))

    @classmethod
    def hash_object(cls, path: str, type: str, write: bool) -> None:
        with open(path, "rb") as fd:
            obj = cls.object_from_data(fd, type.encode())
            print(sha)
