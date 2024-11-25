import hashlib
import zlib
from dataclasses import dataclass
from typing import BinaryIO, Self


@dataclass
class GitObjectBytes:
    """Class representing a serialized GitObject"""
    data: bytes

    def get_hash(self) -> str:
        return hashlib.sha1(self.data).hexdigest()

    def get_compressed(self):
        return zlib.compress(self.data)

    @classmethod
    def from_compressed(cls, compressed: bytes) -> "GitObjectBytes":
        return cls(zlib.decompress(compressed))

    @classmethod
    def from_stored(cls, f: BinaryIO) -> Self:
        return cls.from_compressed(f.read())

    def to_stored(self, f: BinaryIO) -> None:
        f.write(self.get_compressed())