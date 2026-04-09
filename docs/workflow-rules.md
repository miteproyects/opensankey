# Workflow Rules

## Git Push

After every code change, always provide Sebastián the full terminal command to commit and push. Format:

```
git add -A && git commit -m "<commit message>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>" && git push
```

- Commit message: short title + optional one-line description
- Always include `Co-Authored-By` line
- Always include `&& git push` at the end
- Send as a single copy-pasteable block
