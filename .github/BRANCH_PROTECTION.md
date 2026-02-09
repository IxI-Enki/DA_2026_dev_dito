# Branch Protection Rules for `master`

> **Status**: Partially applied.
> Branch protection rules require GitHub Pro for private repositories.
> Auto-delete of branches on merge has been disabled via repository settings.

## Applied Settings

- **Delete branch on merge**: DISABLED (applied 2026-02-05)

## Pending Rules (apply when GitHub Pro is available or repo is made public)

Apply via: Settings > Branches > Branch protection rules > Add rule for `master`

### Required Settings

1. **Require a pull request before merging**
   - Required approving reviews: 1
   - Dismiss stale pull request approvals when new commits are pushed: No
   - Require review from Code Owners: No

2. **Require status checks to pass before merging**
   - Require branches to be up to date before merging: Yes
   - Required checks:
     - `Lint Python`
     - `Validate Spec`
     - `Python Tests`
     - `Docker Validate`
     - `Secret Scan`

3. **Do NOT allow force pushes**

4. **Do NOT allow deletions**

5. **Do NOT automatically delete head branches** (already applied)

### How to Apply via CLI (when available)

```powershell
$body = @'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["Lint Python", "Validate Spec", "Python Tests", "Docker Validate", "Secret Scan"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
'@
$body | gh api repos/IxI-Enki/DA_2026_dev_dito/branches/master/protection -X PUT --input -
```
