from abc import abstractmethod
import hashlib

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from git_repository import GitRepository


class GitObject:
    def __init__(self, data: bytes=None) -> None:
        if data is not None:
            self.deserialize(data)
        else:
            self.init()

    def init(self):
        pass

    @staticmethod
    @abstractmethod
    def fmt() -> bytes:
        raise Exception("Unimplemented!")

    @abstractmethod
    def serialize_data(self, repo: "GitRepository"):
        """The serialize method reads the object's contents from self.data, a byte string, and does
        the appropriate subclass-dependent transformation meaningful representation."""
        raise Exception("Unimplemented!")
    
    def serialize(self, repo: "GitRepository"):
        """Serialize the object with the given type header."""
        data = self.serialize_data(repo)
        result = self.fmt() + b" " + str(len(data)).encode() + b"\x00" + data
        sha = hashlib.sha1(result).hexdigest()
        return result, sha

    @abstractmethod
    def deserialize(self, data):
        raise Exception("Unimplemented!")

class GitBlob(GitObject):

    @staticmethod
    def fmt():
        return b"blob"

    def serialize_data(self, _repo: "GitRepository") -> bytes:
        return self.blobdata

    def deserialize(self, data: bytes) -> None:
        self.blobdata = data