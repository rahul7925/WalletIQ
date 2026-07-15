import os
import sys
import json
import base64
import urllib.request
import urllib.error

# Config
OWNER = "rahul7925"
REPO = "WalletIQ"
BRANCH = "main"

def load_gitignore():
    ignored = {".git", "venv", ".venv", "__pycache__", ".idea", ".vscode", "instance", "logs", ".env", "uploads"}
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # remove trailing slash
                    if line.endswith("/"):
                        line = line[:-1]
                    ignored.add(line)
    return ignored

def get_all_files(ignored):
    files_to_upload = []
    for root, dirs, files in os.walk("."):
        # filter ignored directories
        dirs[:] = [d for d in dirs if d not in ignored and not d.startswith(".")]
        for file in files:
            path = os.path.relpath(os.path.join(root, file), ".")
            # check if file or its parent directories are in ignored list
            parts = path.split(os.sep)
            if any(p in ignored for p in parts) or file.endswith(".pyc") or file.endswith(".pyo"):
                continue
            # replace backslash with forward slash for GitHub paths
            github_path = path.replace(os.sep, "/")
            files_to_upload.append((path, github_path))
    return files_to_upload

def make_request(url, method, headers, data=None):
    req = urllib.request.Request(url, headers=headers, method=method)
    if data:
        req.data = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
        sys.exit(1)
    except Exception as e:
        print(f"Error making request: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python push_to_github.py <GITHUB_PERSONAL_ACCESS_TOKEN>")
        sys.exit(1)

    token = sys.argv[1]
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "WalletIQ-Deployer"
    }

    ignored = load_gitignore()
    files = get_all_files(ignored)
    print(f"Found {len(files)} files to commit.")

    # 1. Get reference to the branch to retrieve parent SHA
    print("Retrieving remote ref...")
    ref_url = f"https://api.github.com/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}"
    ref_data = make_request(ref_url, "GET", headers)
    parent_commit_sha = ref_data["object"]["sha"]
    print(f"Parent Commit SHA: {parent_commit_sha}")

    # 2. Get the tree SHA of parent commit
    commit_url = f"https://api.github.com/repos/{OWNER}/{REPO}/git/commits/{parent_commit_sha}"
    commit_data = make_request(commit_url, "GET", headers)
    parent_tree_sha = commit_data["tree"]["sha"]
    print(f"Parent Tree SHA: {parent_tree_sha}")

    # 3. Create blob for each file
    tree_entries = []
    for idx, (local_path, github_path) in enumerate(files):
        print(f"[{idx+1}/{len(files)}] Creating blob for {github_path}...")
        try:
            with open(local_path, "rb") as f:
                content_b64 = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            print(f"Failed to read file {local_path}: {e}")
            continue

        blob_url = f"https://api.github.com/repos/{OWNER}/{REPO}/git/blobs"
        blob_data = make_request(blob_url, "POST", headers, {
            "content": content_b64,
            "encoding": "base64"
        })
        
        tree_entries.append({
            "path": github_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_data["sha"]
        })

    # 4. Create new tree
    print("Creating new tree on GitHub...")
    tree_url = f"https://api.github.com/repos/{OWNER}/{REPO}/git/trees"
    tree_data = make_request(tree_url, "POST", headers, {
        "base_tree": parent_tree_sha,
        "tree": tree_entries
    })
    new_tree_sha = tree_data["sha"]
    print(f"New Tree SHA: {new_tree_sha}")

    # 5. Create new commit
    print("Creating commit...")
    commit_post_url = f"https://api.github.com/repos/{OWNER}/{REPO}/git/commits"
    new_commit_data = make_request(commit_post_url, "POST", headers, {
        "message": "feat: deploy production ready WalletIQ X release",
        "tree": new_tree_sha,
        "parents": [parent_commit_sha]
    })
    new_commit_sha = new_commit_data["sha"]
    print(f"New Commit SHA: {new_commit_sha}")

    # 6. Update reference
    print("Updating branch pointer...")
    ref_patch_url = f"https://api.github.com/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}"
    make_request(ref_patch_url, "PATCH", headers, {
        "sha": new_commit_sha,
        "force": True
    })

    print("Success! Project successfully pushed to GitHub repository!")


if __name__ == "__main__":
    main()
