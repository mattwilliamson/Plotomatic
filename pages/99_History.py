import streamlit as st
from streamlit_timeline import timeline
from plotomatic.git_utils import get_repo, get_commits
from project_manager import ProjectManager
from git import NULL_TREE
import json

st.set_page_config(page_title="Git History Viewer", layout="wide")
st.title("Git History Viewer")

# Retrieve current project path from session state or ProjectManager
pm = ProjectManager()
project_path = pm.get_current_project_path()

if not project_path:
    st.error("No project is currently selected. Please select a project first.")
else:
    # Initialize the repository
    repo = get_repo(project_path)
    commits = get_commits(project_path)

    # Sort commits chronologically (oldest first)
    commits = sorted(commits, key=lambda c: c.committed_datetime)

    if not commits:
        st.write("No commits found in this repository.")
    else:
        # Retrieve query parameters
        query_params = st.query_params
        selected_commit_param = query_params.get("commit")

        if selected_commit_param:
            # Show the diff viewer for the selected commit
            commit = next((c for c in commits if c.hexsha.startswith(selected_commit_param)), None)
            if commit:
                st.subheader("Commit Details")
                st.write(f"**Commit:** {commit.hexsha}")
                st.write(f"**Author:** {commit.author.name} <{commit.author.email}>")
                st.write(f"**Date:** {commit.committed_datetime}")
                st.write("**Message:**")
                st.code(commit.message, language="text")

                # Diff viewer logic
                st.subheader("Diff")
                if commit.parents:
                    parent_commit = commit.parents[0]
                    diffs = parent_commit.diff(commit, create_patch=True)
                else:
                    diffs = commit.diff(NULL_TREE, create_patch=True)

                if diffs:
                    for diff in diffs:
                        file_path = diff.b_path or diff.a_path or "unknown file"
                        change_type = diff.change_type
                        st.write(f"### File: {file_path} ({change_type})")
                        diff_text = diff.diff.decode("utf-8", errors="replace")
                        st.code(diff_text, language="diff")
                else:
                    st.write("No differences found.")
            else:
                st.error("Commit not found.")
        else:
            # Show the timeline if no commit is selected
            timeline_events = []
            commit_options = []

            for commit in commits:
                if commit.parents:
                    parent_commit = commit.parents[0]
                    diffs = parent_commit.diff(commit, create_patch=True)
                else:
                    # First commit compared to an empty tree
                    diffs = commit.diff(NULL_TREE, create_patch=True)

                added_files = []
                modified_files = []
                deleted_files = []

                for diff in diffs:
                    change_type = diff.change_type
                    file_path = diff.b_path or diff.a_path
                    if change_type == "A":
                        added_files.append(file_path)
                    elif change_type == "D":
                        deleted_files.append(file_path)
                    elif change_type in ("M", "R", "C", "T"):
                        modified_files.append(file_path)

                # Construct a URL that links to this commit
                commit_link = f"?commit={commit.hexsha}#git-history-viewer"

                # https://timeline.knightlab.com/docs/media-types.html
                event = {
                    "start_date": {
                        "year": commit.committed_datetime.year,
                        "month": commit.committed_datetime.month,
                        "day": commit.committed_datetime.day,
                        "hour": commit.committed_datetime.hour,
                        "minute": commit.committed_datetime.minute,
                    },
                    "text": {
                        "headline": commit.message.split('\n')[0],
                        "text": f"<p><strong>Author:</strong> {commit.author.name} <{commit.author.email}><br>"
                                f"<strong>Commit:</strong> {commit.hexsha}<br>"
                                f"<strong>Files Added:</strong><br>"
                                + "<br>".join(f"<code>{file}</code>" for file in added_files)
                                + f"<br><strong>Files Modified:</strong><br>"
                                + "<br>".join(f"<code>{file}</code>" for file in modified_files)
                                + f"<br><strong>Files Deleted:</strong><br>"
                                + "<br>".join(f"<code>{file}</code>" for file in deleted_files)
                                + "</p>",
                    },
                    "media": {
                        "url": "/app/static/view_commit.webp",
                        "thumbnail": "/app/static/view_commit.webp",
                        "link": commit_link,
                        "caption": "View Commit Details",
                    },
                }

                timeline_events.append(event)
                commit_options.append(f"{commit.hexsha[:7]} - {commit.message.splitlines()[0]}")

            # Construct timeline data
            timeline_data = {
                "title": {
                    "text": {
                        "headline": f"Git History for {project_path}",
                        "text": "A timeline of Git commits, including file changes.",
                    },
                },
                "events": timeline_events,
            }

            # Render the timeline
            timeline(json.dumps(timeline_data), height=600)
