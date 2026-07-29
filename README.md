# DataRakshak

DataRakshak is a Windows desktop prototype for secure data-wiping
demonstration, verification, audit logging and digitally signed
certificate generation.

## Current Project Mode

The current version safely supports:

- Fake test-disk creation
- Single-pass zero overwrite
- Full wipe verification
- Progress tracking
- Background-thread operations
- SQLite wipe-job history
- Tamper-evident audit logging
- PDF, JSON and QR certificates
- SHA-256 certificate hashing
- Ed25519 digital signatures
- Certificate tamper detection
- Read-only USB storage detection
- Windows EXE packaging

## Important Safety Notice

Real physical USB wiping is disabled in this prototype.

USB devices are detected only in read-only information mode.
The wiping engine is restricted to:

```text
lab/test_disk.img