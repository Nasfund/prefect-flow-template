"""One-time (idempotent) setup of the Prefect blocks this template can use.

Run once per server/workspace to support the recommended non-interactive git auth
(the inline-token-in-URL approach in the README): this creates the `github-pat`
Secret block that Prefect renders into the clone URL at deploy time.

    # PowerShell:  $env:GITHUB_PAT = "ghp_xxx"
    # bash:        export GITHUB_PAT=ghp_xxx
    python setup_blocks.py
"""

import os

from prefect.blocks.system import Secret
from prefect_github import GitHubCredentials

token = os.environ["GITHUB_PAT"]

# Store the PAT as a Secret block (source of truth; referenced by the inline-token
# git URL:  https://x-access-token:{{ prefect.blocks.secret.github-pat }}@... ).
Secret(value=token).save(name="github-pat", overwrite=True)

# Also expose it as a GitHubCredentials block for any deployment that prefers the
# built-in `git_clone` pull step over the shell-based sync.
token = Secret.load("github-pat").get()
GitHubCredentials(token=token).save(name="github-prefect-demo", overwrite=True)

print("Blocks saved: secret/github-pat, github-credentials/github-prefect-demo")
