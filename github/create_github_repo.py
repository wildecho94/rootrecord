# create_github_repo.py
"""
Script to create a new blank GitHub repository using the GitHub API.
Requires a Personal Access Token (PAT) with 'repo' scope.
"""

import requests
import json
import os
from getpass import getpass

def create_github_repo(repo_name, description="", private=False, token=None):
    """
    Create a new blank GitHub repository.
    
    Args:
        repo_name (str): Name of the repository
        description (str): Optional repo description
        private (bool): Whether the repo should be private
        token (str): GitHub Personal Access Token (will prompt if not provided)
    """
    if not token:
        token = getpass("Enter your GitHub Personal Access Token: ").strip()
        if not token:
            print("Token is required!")
            return

    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    payload = {
        "name": repo_name,
        "description": description,
        "private": private,
        "auto_init": False,          # No README, .gitignore or license
        "has_issues": True,
        "has_projects": False,
        "has_wiki": False,
    }

    print(f"\nCreating repository: {repo_name}...")
    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code == 201:
        repo_data = response.json()
        repo_url = repo_data["html_url"]
        ssh_url = repo_data["ssh_url"]
        print(f"\nSUCCESS! Repository created:")
        print(f"  Web URL:  {repo_url}")
        print(f"  SSH URL:  {ssh_url}")
        print(f"  Clone:    git clone {ssh_url}")
    else:
        try:
            error = response.json()
            print(f"\nERROR ({response.status_code}): {error.get('message', 'Unknown error')}")
            if 'errors' in error:
                for e in error['errors']:
                    print(f"  - {e.get('message')}")
        except:
            print(f"\nERROR: Failed to create repository (status {response.status_code})")
            print(response.text)


def main():
    print("Create a new blank GitHub repository\n")
    
    repo_name = input("Repository name: ").strip()
    if not repo_name:
        print("Repository name is required!")
        return

    description = input("Description (optional): ").strip()
    private_input = input("Private repository? (y/n): ").strip().lower()
    private = private_input in ('y', 'yes', '1')

    create_github_repo(repo_name, description, private)


if __name__ == "__main__":
    main()