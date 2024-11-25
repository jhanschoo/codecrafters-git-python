import sys

from app.git_object import GitObject
from app.git_object_bytes import GitObjectBytes
from app.git_repository import GitRepository


def init(**kwargs):
    GitRepository.create(kwargs["path"])

def cat_file(**kwargs):
    name: str = kwargs["object"]
    fmt: str = kwargs["type"]
    # if type="-p", fmt requires inference. For now only blobs are supported
    if fmt == "-p":
        fmt = "blob"
    repo: GitRepository = GitRepository.find(required=True)
    fmt = GitRepository.object_find(name, fmt=fmt)
    obj_bytes = repo.object_retrieve(fmt)
    if obj_bytes is None:
        raise Exception("Unable to retrieve")
    _, _, data = GitObject.bytes_as_metadata_and_data(obj_bytes)
    sys.stdout.buffer.write(data)

def hash_object(**kwargs):
    path: str = kwargs["path"]
    fmt: str = kwargs["type"]
    write: bool = kwargs["write"]
    with open(path, "rb") as fd:
        obj = GitObject.from_data(fd, fmt.encode())
        obj_bytes = obj.to_bytes()
        sha = obj_bytes.get_hash()
        print(sha)
        if write:
            repo: GitRepository = GitRepository.find(required=True)
            repo.object_store_at(obj_bytes, sha)