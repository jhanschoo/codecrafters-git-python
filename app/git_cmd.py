import os.path
import sys

from app.git_object import GitObject, GitTree, GitTreeLeaf
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

def ls_tree(**kwargs):
    name: str = kwargs["tree"]
    recurse: bool = kwargs["recurse"]
    tree_entries: bool = kwargs["tree_entries"]
    name_only: bool = kwargs["name_only"]
    repo: GitRepository = GitRepository.find(required=True)
    fmt = GitRepository.object_find(name, fmt="tree")
    lines: list[str] = []
    obj_bytes = repo.object_retrieve(fmt)
    if obj_bytes is None:
        raise Exception("Unable to retrieve")
    def leaf_repr(leaf: GitTreeLeaf, prefix: str | None=None):
        if name_only:
            return leaf.filename
        else:
            return leaf.sprint(prefix)
    def ls_tree_aux(obj_bytes: GitObjectBytes, prefix: str | None = None):
        obj = GitObject.from_bytes(obj_bytes)
        if not isinstance(obj, GitTree):
            raise Exception("Not a tree")
        for leaf in obj.items:
            if leaf.fmt == "tree":
                if not recurse or tree_entries:
                    lines.append(leaf_repr(leaf, prefix))
                if recurse:
                    child_obj_bytes = repo.object_retrieve(leaf.sha)
                    ls_tree_aux(child_obj_bytes, leaf.filename if prefix is None else os.path.join(prefix, leaf.filename))
            else:
                lines.append(leaf_repr(leaf, prefix))
    ls_tree_aux(obj_bytes)
    print("\n".join(lines))