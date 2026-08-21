# Development

This guide describes the recommended development workflow for Betabox Robotics.

Betabox Robotics is developed directly against the running Betabox platform, with software tests used where practical and real-hardware validation used when physical behavior cannot be proven automatically.

The development model assumes the current centralized runtime architecture.

## Development Environment

The supported development environment is based on:

- Raspberry Pi OS Bookworm
- Python 3.11
- `/opt/libs/betabox_robotics` as the source checkout
- `/opt/betabox/venv` as the primary Betabox Python environment
- Git feature branches
- Python `unittest`
- real Betabox hardware for physical validation

On a deployed robot, activate the Betabox environment with:

```bash
source /opt/betabox/venv/bin/activate
```

Verify the interpreter:

```bash
which python
python --version
```

The expected Python version is:

```text
Python 3.11.x
```

## Source Checkout

The normal source checkout is:

```text
/opt/libs/betabox_robotics
```

Move into the repository:

```bash
cd /opt/libs/betabox_robotics
```

Inspect the current state before making changes:

```bash
git status
git branch --show-current
git log -1 --oneline
```

Development should normally happen on a feature branch rather than directly on `main`.

## Branch Workflow

Create a feature branch for new work:

```bash
git switch -c feat/my-change
```

Examples:

```text
feat/runtime-health
feat/calibration-reset
fix/manual-drive-grayscale
refactor/status-model
```

Before switching branches, make sure the current working tree is understood:

```bash
git status
```

Commit, stash, or intentionally discard local changes before switching.

## Updating Before Development

Fetch the latest remote state:

```bash
git fetch origin
```

For work based on `main`:

```bash
git switch main
git pull --ff-only origin main
```

Then create the feature branch:

```bash
git switch -c feat/my-change
```

Avoid building new work on top of a stale local `main`.

## Editable Installation

The normal Betabox deployment installs the repository in editable mode into:

```text
/opt/betabox/venv
```

This means changes made in:

```text
/opt/libs/betabox_robotics
```

are immediately visible to Python using the active Betabox environment.

A normal source edit does not require reinstalling the package.

For example:

```bash
source /opt/betabox/venv/bin/activate
python -c "import betabox_robotics; print(betabox_robotics.__version__)"
```

## When Reinstallation Is Required

Source-only Python changes generally do not require rerunning the installer.

Reinstallation or deployment updates may be required when changing areas such as:

- Python dependencies
- system packages
- systemd units
- sudoers rules
- JupyterHub configuration
- provisioning
- users or groups
- boot configuration
- deployment assets
- service permissions
- filesystem layout

In those cases, inspect the deployment change and run:

```bash
./deployment/install.sh
```

when appropriate.

A reboot may also be required for changes affecting boot configuration or hardware initialization.

## Service Restarts

Long-running services must be restarted before they will use changed Python code.

Examples include:

- robot runtime
- Launchpad
- vision service
- monitor

Use the Betabox CLI where available:

```bash
betabox restart <service>
```

Or systemd directly:

```bash
sudo systemctl restart <service>
```

Then verify:

```bash
systemctl status <service>
```

For live logs:

```bash
journalctl -u <service> -f
```

## Centralized Runtime Development

The runtime is the long-lived owner of normal robot hardware.

This has an important development consequence:

> Do not bypass the runtime simply because direct hardware construction is easier during application development.

Normal application layers should use:

```text
Public Robot API
RobotRuntimeClient
Platform services
```

rather than independently constructing:

- Drive
- Motors
- Servos
- CameraMount
- robot sensors
- complete robot hardware

Direct hardware construction is appropriate mainly for isolated hardware-layer testing and debugging.

## Runtime Ownership During Development

Only one application may own actuator control at a time.

If an operation fails because another application owns control, investigate the owner rather than bypassing the runtime.

Useful state can be inspected with:

```bash
betabox status
```

or the runtime section of JSON status where needed.

A control conflict is not a hardware failure.

## Student API Development

The preferred application-facing API is:

```python
from betabox_robotics import Robot

robot = Robot.default()
```

The concrete car implementation is also available where appropriate:

```python
from betabox_robotics import BetaboxCar

robot = BetaboxCar()
```

New student-facing examples and curriculum should prefer the public Robot API rather than low-level runtime or hardware interfaces unless the lesson explicitly teaches those layers.

## Code Style

Betabox Robotics uses modern Python style appropriate to Python 3.11.

General expectations include:

- explicit type annotations
- narrow exception handling
- clear ownership and cleanup
- immutable models where appropriate
- small validation helpers
- meaningful names
- clear public/private boundaries
- no hidden fallback behavior that changes hardware semantics

Avoid catching:

```python
except Exception:
```

unless there is a very specific architectural reason and the exception is immediately re-raised or safely isolated.

Prefer catching only the exceptions the caller can meaningfully handle.

## Type Safety

The codebase uses static typing extensively.

Common expectations include:

- avoid unnecessary `cast()` when the type can be narrowed naturally
- avoid `Any` where a meaningful protocol or concrete type is available
- use read-only protocol properties where structural compatibility requires them
- use `Self` for fluent/context-manager return types where appropriate
- validate runtime data crossing process or HTTP boundaries
- do not assume JSON or protocol payloads are correctly typed

Type-checker warnings should be investigated rather than silenced automatically.

## Protocols

Protocols are useful when different implementations expose the same read-only interface.

When a protocol is intended to describe data produced by another object, prefer read-only properties where mutation is not required.

For example:

```python
class SnapshotDataInterface(Protocol):
    @property
    def data(self) -> bytes:
        ...

    @property
    def timestamp(self) -> float:
        ...
```

This avoids structural typing conflicts with immutable data classes.

## Validation

Validation should happen at the layer that owns the rule.

Examples:

```text
Hardware range
    → hardware/subsystem

Robot operating limit
    → robot configuration/subsystem

Calibration validity
    → calibration model/service

Permission
    → Launchpad server

HTTP payload shape
    → route

Runtime protocol payload
    → runtime protocol/client
```

Do not rely exclusively on browser-side validation for platform invariants.

Client-side validation is useful for immediate feedback, but server-side code remains authoritative.

## Exceptions

Errors should be translated as they move upward through the architecture.

Conceptually:

```text
HardwareError
     ↓
Subsystem / runtime error
     ↓
Application service error
     ↓
HTTP / CLI presentation
```

Do not leak low-level implementation errors directly to students when a higher-level error is more meaningful.

Likewise, do not convert every error into a generic:

```text
Robot failed
```

when the platform knows whether the actual issue is:

- robot busy
- invalid calibration
- runtime unavailable
- sensor unavailable
- storage failure
- service failure

## Testing Framework

Betabox Robotics uses Python's built-in `unittest` framework.

Run the current checked-in test suite with:

```bash
python -m unittest discover -s tests
```

Individual modules can be run with:

```bash
python -m unittest tests.<package>.<module>
```

For example:

```bash
python -m unittest tests.runtime.test_client
```

## Current Test Coverage

The checked-in automated tests currently focus primarily on the centralized runtime.

That means passing the automated suite does not currently prove that all major packages are regression-tested.

Additional coverage should be rebuilt as the platform stabilizes.

High-priority areas include:

- calibration
- Launchpad
- platform health
- status
- diagnostics
- monitoring and events
- sensors
- public Robot API
- services

## Test Boundaries

Testing should follow the platform architecture.

### Hardware unit tests

Verify software behavior of individual hardware abstractions.

Examples:

- validation
- command translation
- retries
- cleanup
- state transitions

These tests should normally mock physical interfaces.

### Hardware validation tests

Run against physical hardware.

Examples:

- motor turns
- servo moves
- ADC reads
- ultrasonic works
- grayscale readings change

These tests prove physical behavior that software mocks cannot.

### Subsystem tests

Verify reusable subsystem behavior.

Examples:

- drive
- sensors
- camera mount
- audio
- vision

### Runtime tests

Verify:

- protocol encoding and decoding
- client behavior
- control acquisition
- control release
- token validation
- competing owners
- read-only access during active control
- runtime errors

### Service tests

Verify:

- calibration
- status
- platform health
- diagnostics
- monitoring
- events
- accounts
- backup/recovery

### Launchpad tests

Verify:

- routes
- permissions
- context
- workspaces
- API serialization
- Manual Drive ownership
- calibration behavior
- error translation

## Test Naming

Test names should describe behavior rather than implementation.

Prefer:

```python
def test_acquire_control_rejects_empty_owner(self) -> None:
```

over:

```python
def test_control_1(self) -> None:
```

Tests should make the expected contract obvious.

## Regression Tests

Every bug fix should add a regression test when the failure can be represented automatically.

For example, the grayscale calibration bug should be protected by tests covering:

```text
difference = 0      reject
difference = 99     reject
difference = 100    accept
```

A regression test should reproduce the condition that caused the bug, not merely exercise nearby code.

## Hardware Validation

Some changes cannot be validated fully through automated tests.

Examples include:

- motor movement
- steering movement
- camera mount movement
- audible speaker output
- physical camera framing
- sensor disconnection behavior

These changes require real-robot validation.

## Validation Mental Model

Use this distinction when deciding what a test proves.

### Hardware validation

Validates an individual hardware abstraction against the physical device.

### Subsystem validation

Validates a reusable subsystem using configured robot wiring.

### Robot validation

Validates the composed Betabox car.

### Platform validation

Validates the complete running platform, including:

- runtime
- services
- Launchpad
- JupyterHub
- monitoring
- health
- deployment behavior

Passing one layer does not automatically validate the layers above it.

## Safe Physical Testing

Before running hardware-affecting tests:

- place the robot on a safe surface
- ensure there is clear movement space
- keep hands away from actuators
- verify battery condition
- confirm the correct control owner
- stop Manual Drive or student programs that may own control
- be prepared to stop the robot

Motor calibration and drive tests require particular care because the robot may move immediately.

## Platform Status During Development

Useful commands include:

```bash
betabox status
betabox doctor
betabox services
betabox events
```

Use these before and after significant runtime, service, or hardware changes.

For JSON status inspection:

```bash
betabox status --json
```

Use `jq` when focused inspection is useful.

For example:

```bash
betabox status --json | jq '.runtime'
```

## Diagnostics During Development

`betabox doctor` is useful when code changes affect:

- runtime startup
- hardware initialization
- services
- sensors
- camera
- JupyterHub
- host system behavior

A failed automated unit test and a failed platform diagnostic represent different things.

Both may matter.

## Events During Development

The Events system is useful for changes affecting monitored state.

Run:

```bash
betabox events
```

When testing a monitored condition, verify both failure and recovery where applicable.

For example:

```text
Ultrasonic sensor became unavailable
Ultrasonic sensor became available
```

A monitor that detects failure but not recovery is incomplete.

## Boot Testing

Changes affecting any of these areas should include reboot validation:

- runtime service
- boot announcements
- systemd dependencies
- hardware initialization
- monitoring
- vision startup
- JupyterHub
- Wi-Fi fallback
- hostname configuration
- deployment

A service working after manual restart does not prove that the platform boots correctly.

## Fresh-Install Testing

Deployment changes should eventually be tested from a fresh supported Raspberry Pi OS image.

A fresh-install test is particularly important after changes to:

- `deployment/bootstrap.sh`
- `deployment/install.sh`
- provisioning
- systemd units
- sudoers
- user creation
- groups
- JupyterHub
- boot configuration
- service permissions

Existing development robots may contain state that hides deployment bugs.

## Git Review Before Commit

Before committing:

```bash
git status
git diff --check
git diff
```

`git diff --check` should normally produce no output.

Review the diff carefully for:

- accidental debug code
- branch-specific deployment changes
- hard-coded local paths
- stale comments
- temporary logging
- removed files that are still referenced
- unrelated changes

## Searching the Repository

`rg` is the preferred repository search tool.

Examples:

```bash
rg -n 'pattern' .
```

Search only Python:

```bash
rg -n 'pattern' . --glob '*.py'
```

Exclude generated or irrelevant content where appropriate:

```bash
rg -n 'pattern' . \
    --glob '!__pycache__/**' \
    --glob '!*.pyc'
```

Repository-wide searches are especially useful during migrations and cleanup.

## Legacy-Code Audits

After a migration, search for the old API or architecture explicitly.

For example:

```bash
rg -n \
'OldClass|old_function|old_owner_name' \
. \
--glob '*.py'
```

Do not assume the migration is complete merely because the main path works.

Check:

- services
- Launchpad
- CLI
- tests
- deployment
- public exports
- compatibility modules

## Static Analysis

IDE/type-checker warnings should be resolved before considering a refactor complete.

Examples worth investigating include:

- incompatible override types
- unknown types
- unnecessary casts
- impossible `isinstance` checks
- unreachable branches
- incompatible protocol attributes

A clean runtime test suite does not replace static analysis.

## Public API Changes

Be deliberate when changing public interfaces.

Public APIs include areas such as:

```python
from betabox_robotics import Robot
from betabox_robotics import BetaboxCar
```

and other exported package interfaces.

Before removing or renaming a public symbol:

1. search repository usage;
2. check Launchpad and services;
3. check curriculum;
4. check external compatibility requirements;
5. consider a compatibility alias where appropriate.

For example, the legacy `Car` name may remain as a compatibility alias even though new code should prefer `BetaboxCar`.

## Internal API Changes

Internal implementation APIs can evolve more freely, but repository-wide consumers still need to be migrated together.

Before changing an internal interface, search:

```bash
rg -n 'SymbolName' .
```

Then update all active callers in one coherent change where practical.

## Runtime Protocol Changes

Changes to runtime commands or protocol payloads should update all related layers together.

Typical affected areas include:

```text
runtime/protocol.py
runtime/server.py
runtime/runtime.py
runtime/client.py
runtime/control.py
tests/runtime/
```

Do not update only the client or only the server.

Protocol changes should remain backward-compatible only when that compatibility is intentionally required.

## Launchpad Changes

Launchpad features often cross several files.

A typical change may involve:

```text
route
service
template
DOM bindings
JavaScript
CSS
tests
```

Do not assume adding only an HTTP route completes a browser feature.

When adding a new DOM element:

```text
HTML
    ↔
dom.js
    ↔
page/module JS
```

must remain synchronized.

Missing element IDs can cause an entire page module to fail during initialization.

## Calibration Changes

Calibration changes often require updates across:

```text
calibration model
CalibrationService
CalibrationHardware
Launchpad route
Launchpad UI
tests
```

Persisted validation belongs server-side even when Launchpad also validates it.

Physical previews must continue to use centralized runtime control.

## Platform-Health Changes

A new health condition may affect several interfaces.

Consider:

- raw status collection
- health evaluation
- diagnostics
- monitor snapshot
- event transitions
- boot verification
- boot announcements
- CLI status
- Launchpad Status
- Launchpad Diagnostics

Do not patch only the browser when the condition is platform-wide.

## Documentation Changes

Documentation should describe the current implementation.

Code is authoritative.

When changing architecture or behavior, update the relevant document in the same branch.

Current documentation responsibilities are:

```text
README.md
    → project landing page

docs/architecture.md
    → platform layering and boundaries

docs/runtime.md
    → centralized runtime and control ownership

docs/installation.md
    → deployment and update procedures

docs/launchpad.md
    → browser application

docs/platform-health.md
    → status, health, diagnostics, monitoring, events

docs/calibration.md
    → calibration model and workflow

docs/hardware.md
    → hardware abstractions and physical hardware

docs/development.md
    → development and testing workflow
```

Avoid recreating large duplicated documentation trees unless there is a concrete need.

## Commit Messages

Use concise commit messages that describe the intent of the change.

Common prefixes include:

```text
feat:
fix:
refactor:
docs:
test:
chore:
```

Examples:

```text
feat: add centralized robot runtime
fix: reject invalid grayscale calibration
refactor: unify platform health evaluation
docs: rebuild platform architecture documentation
test: add runtime control regression coverage
```

## Before Pushing

Run the appropriate validation for the change.

At minimum for Python changes:

```bash
python -m unittest discover -s tests
git diff --check
git status
```

For platform changes, also consider:

```bash
betabox status
betabox doctor
```

For service changes:

```bash
betabox services
```

For monitoring changes:

```bash
betabox events
```

For hardware changes, perform the appropriate physical validation.

## Commit and Push

Stage only intended changes:

```bash
git add <files>
```

Review:

```bash
git status
git diff --cached
```

Commit:

```bash
git commit -m "type: description"
```

Push the feature branch:

```bash
git push -u origin <branch>
```

## Merge Workflow

Before merging:

1. make sure the feature branch is clean;
2. run automated tests;
3. perform required real-hardware validation;
4. verify deployment implications;
5. review documentation changes;
6. fetch the latest remote state;
7. merge into `main`.

After merging, confirm:

```bash
git switch main
git status
git log --oneline --decorate -10
```

Verify local and remote `main` when needed:

```bash
git rev-parse main
git rev-parse origin/main
```

## Deployment Branch Safety

Development branches may temporarily be used for installation testing.

Before the work is considered complete, ensure production deployment returns to:

```text
main
```

For example, `deployment/bootstrap.sh` should normally track:

```bash
BRANCH="main"
```

Do not accidentally leave a temporary feature branch as the production bootstrap source.

## Post-Merge Validation

After a significant merge, verify the running robot from `main`.

Useful checks include:

```bash
betabox status
betabox doctor
betabox services
```

For changes affecting boot behavior, perform a real reboot:

```bash
sudo reboot
```

Then repeat the checks after startup.

For runtime or ownership changes, also verify:

- Manual Drive
- student Python control
- calibration
- sensor reads
- control conflicts
- release behavior

## Refactoring Strategy

Large architectural changes should be performed incrementally.

A good pattern is:

```text
Define new boundary
      ↓
Add implementation
      ↓
Add tests
      ↓
Migrate one consumer
      ↓
Validate
      ↓
Migrate remaining consumers
      ↓
Search for legacy usage
      ↓
Delete old path
      ↓
Full validation
```

This is safer than rewriting multiple platform layers without intermediate validation.

## Migration Completion

Do not declare a migration complete based only on successful manual use.

Perform repository-wide searches for:

- old constructors
- old ownership models
- old status logic
- stale imports
- obsolete services
- old deployment references
- compatibility code that is no longer needed

Then distinguish between:

```text
intentional compatibility
```

and:

```text
forgotten legacy code
```

Only the latter should be removed.

## Real-World Debugging

When a platform feature behaves unexpectedly, isolate the layer first.

For example:

```text
Browser problem?
Launchpad route problem?
Application-service problem?
Runtime problem?
Subsystem problem?
Hardware problem?
```

Use the narrowest test that can distinguish between those possibilities.

Useful tools include:

```bash
rg
git diff
systemctl
journalctl
betabox status
betabox doctor
betabox events
```

Avoid rewriting multiple layers until the failing boundary is understood.

## Architectural Rules

The following rules should guide development:

1. Use the highest appropriate public interface.
2. Do not bypass centralized robot ownership from normal applications.
3. Applications own control sessions; the runtime owns hardware.
4. Read-only operations should not acquire actuator control unnecessarily.
5. Reusable behavior belongs below UI layers.
6. Browser validation does not replace server-side validation.
7. Catch only errors that can be meaningfully handled.
8. Keep configuration, calibration, and hardware behavior separate.
9. Status, diagnostics, monitoring, events, and boot health should share platform definitions.
10. Automated tests and physical validation prove different things.
11. Hardware-affecting changes require real-robot validation.
12. Deployment changes require deployment testing.
13. A manually restarted service is not proof of correct boot behavior.
14. Search for legacy consumers before deleting old APIs.
15. Documentation should describe current code.
16. Feature branches should not become accidental production deployment branches.
17. Public API changes should be deliberate.
18. Protocol changes must update both sides together.
19. New Launchpad features should update all required HTML, JS, route, and service layers coherently.
20. Prefer incremental migrations with validation between steps.

## Related Documentation

- [Platform Architecture](architecture.md)
- [Central Robot Runtime](runtime.md)
- [Installation](installation.md)
- [Betabox Launchpad](launchpad.md)
- [Platform Health and Diagnostics](platform-health.md)
- [Calibration](calibration.md)
- [Hardware](hardware.md)
