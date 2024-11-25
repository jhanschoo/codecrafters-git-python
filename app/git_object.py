from abc import abstractmethod

from typing import TYPE_CHECKING, BinaryIO, Self, Tuple

from app.git_object_bytes import GitObjectBytes

if TYPE_CHECKING:
    from git_repository import GitRepository


class GitObject:
    """Abstract class representing GitObjects"""

    def __init__(self, data: bytes=None) -> None:
        if data is not None:
            self._deserialize_data(data)
        else:
            self.init()

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
        data: bytes = b.data[y+1:]
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
            # case b'commit':
            #     return GitCommit(data)
            # case b'tree':
            #     return GitTree(data)
            # case b'tag':
            #     return GitTag(data)
            case b'blob':
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

    @abstractmethod
    def _deserialize_data(self, data: bytes) -> bytes:
        """The _deserialize_data method takes serialized data
        and stores it in the subclass object"""
        raise Exception("Unimplemented!")

class GitBlob(GitObject):

    @staticmethod
    def fmt():
        return b"blob"

    def _serialize_data(self) -> bytes:
        return self.blobdata

    def _deserialize_data(self, data: bytes) -> None:
        self.blobdata = data