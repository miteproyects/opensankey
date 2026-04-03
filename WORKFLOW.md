# Deployment Workflow

When Claude makes code changes, Claude must stage and commit them automatically so the only command needed in terminal is:

```
git push
```

Claude should always run `git add` and `git commit` on the changed files before telling the user the fix is ready. The user should never need to run anything other than `git push`.
