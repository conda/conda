### Title

Preserve Windows configuration access controls and EFS protection.

### Why

Replacing configuration must preserve access restrictions and encryption.
A preservation failure must leave the existing file unchanged.

### Platforms

- [x] Windows
- [ ] macOS
- [ ] Linux

### Prerequisites

Use PowerShell with the conda build under test on a local NTFS volume. EFS
requires filesystem support and an encryption key for the signed-in account.
Use a disposable directory and synthetic configuration values only.

### Steps

1. Create a `.condarc` containing `changeps1: true` in the disposable directory.
   Store its path in `$qaConfig`.
2. Run `icacls $qaConfig /inheritance:d /deny "*S-1-5-7:(R)"` and record
   `(Get-Acl -LiteralPath $qaConfig).Sddl`.
3. Run `conda config --file $qaConfig --set changeps1 false`. Require exit code
   zero, the new value, and unchanged SDDL. Repeat with `true`.
4. Repeat with a second file inheriting an anonymous-user denial from its parent,
   configured using `icacls` with `/deny "*S-1-5-7:(OI)(CI)(R)"`. Confirm the denial
   remains inherited after writing.
5. Run `cipher /e /a $qaConfig`, then record EFS users and certificate thumbprints
   from `cipher /c $qaConfig`. Change `changeps1` to `false` and require unchanged
   SDDL, readable new contents, and unchanged encryption, EFS users, and thumbprints.
6. Deny writes to the signed-in user's SID using `icacls $qaConfig /deny
   "*<SID>:(W)"`. Record the file hash and SDDL, then attempt to set `changeps1` to
   `true`. Require a nonzero exit code and unchanged hash and SDDL. Remove this
   test denial using `icacls $qaConfig /remove:d "*<SID>"` afterward.
7. Check for `.tmp` files in the disposable directory and remove the directory.

### Pass criteria

Successful writes preserve ownership, DACLs, inheritance, and EFS access.
Denied writes preserve the original file. No staged files remain.

### Out of scope / notes

Persistent `.condarc.lock` files are expected. Record unavailable EFS checks as
not executed. Automated tests check staged-file protection and injected failures.
Audit ACEs, network filesystems, and untrusted directories are outside this scenario.
