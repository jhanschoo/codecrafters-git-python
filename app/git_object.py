import dataclasses
import os.path
from abc import abstractmethod
from operator import attrgetter
from typing import TYPE_CHECKING, BinaryIO, Self, Tuple
from dataclasses import dataclass

from app.git_object_bytes import GitObjectBytes

if TYPE_CHECKING:
    from git_repository import GitRepository


class GitObject:
    """Abstract class representing GitObjects"""

    def init(self):
        pass

    @staticmethod
    @abstractmethod
    def fmt() -> bytes:
        raise Exception("Unimplemented!")

    @classmethod
    def bytes_as_metadata_and_data(cls, b: GitObjectBytes) -> Tuple[bytes, int, bytes]:
        # Note: `decompressobj()` is safer with respect to memory usage, but
        # it would be harder to write correctly.

        # Read object type
        x = b.data.find(b' ')
        fmt: bytes = b.data[0:x]

        # Read and validate object size
        y = b.data.find(b'\x00', x)
        size = int(b.data[x:y].decode("ascii"))
        if size != len(b.data) - y - 1:
            raise Exception(f"Malformed object: bad length")
        data: bytes = b.data[y + 1:]
        return fmt, size, data

    @classmethod
    def from_bytes(cls, raw: GitObjectBytes) -> Self:
        # Note: `decompressobj()` is safer with respect to memory usage, but
        # it would be harder to write correctly.

        fmt, _, data = cls.bytes_as_metadata_and_data(raw)
        return cls.deserialize(data, fmt)

    @classmethod
    def from_data(cls, f: BinaryIO, fmt: bytes) -> Self:
        """deserialize the data in `fd`"""
        return cls.deserialize(f.read(), fmt)

    @classmethod
    def deserialize(cls, data: bytes, fmt: bytes) -> Self:
        """Construct a GitObject from serialized data and format bytes."""
        match fmt:
            # case b"commit":
            #     return GitCommit(data)
            case b"tree":
                return GitTree(data)
            # case b"tag":
            #     return GitTag(data)
            case b"blob":
                return GitBlob(data)
            case _:
                raise Exception(f"Unknown type {fmt.decode("ascii")}!")

    def to_bytes(self) -> GitObjectBytes:
        """Serialize the object into GitObjectBytes."""
        data = self._serialize_data()
        result = self.fmt() + b" " + str(len(data)).encode() + b"\x00" + data
        return GitObjectBytes(result)

    @abstractmethod
    def _serialize_data(self) -> bytes:
        """The _serialize_data method uses data contained
        in the subclass object to returns bytes that are the serialization
        of the subclass object, without type/length/etc metadata"""
        raise Exception("Unimplemented!")


class GitBlob(GitObject):

    def __init__(self, data: bytes):
        self.blobdata = data

    @staticmethod
    def fmt():
        return b"blob"

    def _serialize_data(self) -> bytes:
        return self.blobdata


@dataclass
class GitTreeLeaf:
    mode: bytes
    filename: str
    sha: str

    @property
    def key(self):
        if self.mode.startswith(b"10"):
            return self.filename
        else:
            return self.filename + "/"

    @property
    def fmt(self) -> str:
        # see https://stackoverflow.com/a/8347325/2139851
        match self.mode[:2]:
            case b"04":
                return "tree"
            case b"10":
                return "blob"  # regular file
            case b"12":
                return "blob"  # symlink
            case b"16":
                return "commit"  # submodule
            case _:
                raise Exception(f"malformed mode {str(self.mode)}")

    def __str__(self) -> str:
        return f"{self.mode.decode('ascii')} {self.fmt}\t{self.sha}"

    def sprint(self, prefix=None) -> str:
        return f"{str(self)} {self.filename if prefix is None else os.path.join(prefix, self.filename)}"


class GitTree(GitObject):
    items: list[GitTreeLeaf]

    def __init__(self, data: bytes):
        if data:
            self.items = self.tree_parse(data)
        else:
            self.items = list()

    @staticmethod
    def fmt():
        return b"tree"

    def _serialize_data(self) -> bytes:
        return self.tree_serialize()

    @classmethod
    def tree_parse_one(cls, raw: bytes, start=0) -> tuple[int, GitTreeLeaf]:
        x = raw.find(b' ', start)
        assert (x - start in [5, 6])

        mode = raw[start:x]
        if x-start == 5:
            mode = b"0" + mode

        y = raw.find(b'\x00', x)
        path = raw[x + 1:y]

        raw_sha = int.from_bytes(raw[y + 1:y + 21], "big")
        sha = format(raw_sha, "040x")
        return y + 21, GitTreeLeaf(mode, path.decode("utf8"), sha)

    @classmethod
    def tree_parse(cls, raw: bytes):
        pos = 0
        end = len(raw)
        ret = list()
        while pos < end:
            pos, data = cls.tree_parse_one(raw, pos)
            ret.append(data)
        return ret

    def tree_serialize(self):
        self.items.sort(key=attrgetter("key"))
        ret = b''
        for i in self.items:
            ret += i.mode
            ret += b' '
            ret += i.path.encode("utf8")
            ret += b'\x00'
            sha = int(i.sha, 16)
            ret += sha.to_bytes(20, byteorder="big")
        return ret
