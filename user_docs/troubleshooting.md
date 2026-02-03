# Troubleshooting

## Help modal shows “PDF not available”

Some deployments may not include the overview PDF. If it’s not available:

- Use the **Docs** tab instead
- Or contact support via **Help → Contact**

## Help search returns no docs

The in-app Help search indexes `user_docs/` (user-facing docs).
If you are running from source, ensure `user_docs/` exists in the repo root.

## “Cannot connect to LLM provider”

- Check provider/base URL in **Settings**
- Check backend logs for connectivity errors
- If you can’t resolve it, contact your admin/support team

