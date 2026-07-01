# Betabox System Architecture

**Status:** Foundation  
**Project:** Betabox Robot Platform

---

# Purpose

The System subsystem provides information about the robot platform and
shared system resources.

It exposes platform information through a stable public API while hiding
operating system implementation details.

---

# Responsibilities

The System subsystem is responsible for:

- Robot identity
- Network information
- Shared media directories
- Platform status

Future versions may also provide:

- Service status
- Version information
- Health monitoring
- Diagnostics

---

# Public API

```python
status = robot.system.status()

print(status.hostname)
print(status.ip_addresses)

paths = robot.system.media_paths()

print(paths.pictures)
print(paths.videos)

robot.system.ensure_media_paths()
```
