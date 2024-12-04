# git_utils.py

from git import Repo
from pathlib import Path
import difflib

def create_repo(project_path):
    """Create a Git repository in the given project path."""
    project_path = Path(project_path).resolve()  # Ensure the path is absolute
    if not project_path.exists():
        raise FileNotFoundError(f"Project path does not exist: {project_path}")
    return Repo.init(project_path)

def add_file(repo, file_path):
    """Add a file to the repository."""
    repo.index.add([file_path])

def get_repo(project_path):
    """Get a Git repository object for the given project path."""
    project_path = Path(project_path).resolve()  # Ensure the path is absolute
    if not project_path.exists():
        raise FileNotFoundError(f"Project path does not exist: {project_path}")
    return Repo(project_path)

def get_changed_files(repo):
    """Get a list of changed files in the repository."""
    return [item.a_path for item in repo.index.diff(None)]

def get_diff(repo, file_path):
    """Get the diff of a file."""
    diff_text = ''
    working_dir = repo.working_tree_dir
    file_full_path = Path(working_dir) / file_path
    if file_full_path.exists():
        with open(file_full_path, 'r') as f:
            b_text = f.read()
    else:
        b_text = ''

    try:
        a_blob = repo.head.commit.tree[file_path]
        a_text = a_blob.data_stream.read().decode('utf-8')
    except KeyError:
        a_text = ''

    diff = difflib.unified_diff(
        a_text.splitlines(),
        b_text.splitlines(),
        fromfile='a/' + file_path,
        tofile='b/' + file_path,
        lineterm=''
    )
    diff_text = '\n'.join(diff)
    return diff_text

def commit_changes(repo, message):
    """Commit changes in the repository."""
    repo.index.add([item.a_path for item in repo.index.diff(None)])
    repo.index.commit(message)

def discard_changes(repo):
    """Discard changes in the repository."""
    repo.git.checkout('--', '.')
