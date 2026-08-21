# Calibration

Betabox Robotics supports persistent calibration for the physical differences
between individual robots.

Calibration allows the software platform to compensate for variations in:

- steering center
- camera pan alignment
- camera tilt alignment
- left motor output
- right motor output
- grayscale floor readings
- grayscale line readings

Calibration is normally performed through the Calibration page in Betabox
Launchpad.

## Purpose

Nominal hardware configuration is shared across Betabox robots, but individual
robots may require small adjustments.

Examples include:

- a steering servo whose mechanical center is slightly offset
- a camera mount that does not point straight ahead at its nominal center
- drive motors with slightly different output
- grayscale sensors whose raw floor and line values differ between robots

Calibration records those robot-specific adjustments separately from the base
robot configuration.

Conceptually:

```text
Base Robot Configuration
          +
Saved Robot Calibration
          ↓
Effective Robot Behavior
```

## Architecture

Calibration is split across several layers.

```text
Launchpad Calibration Page
          │
          ▼
Calibration Routes
          │
          ├── CalibrationService
          │       └── validation and persistence
          │
          └── CalibrationHardware
                  └── Robot Runtime
                          └── physical previews
```

This separation is intentional.

The browser is responsible for user interaction.

The calibration service is responsible for persisted calibration state.

The calibration model is responsible for calibration validity.

The calibration hardware layer is responsible for physical preview operations.

The centralized robot runtime remains responsible for robot hardware ownership.

## Calibration Data

The complete calibration model contains four areas:

```text
RobotCalibration
    │
    ├── SteeringCalibration
    ├── CameraMountCalibration
    ├── MotorCalibration
    └── GrayscaleCalibration
```

These values are stored together as one robot calibration document.

## Default Calibration

When no saved calibration exists, the platform uses the default calibration.

The default values represent an uncalibrated robot:

```text
Steering offset       0.0
Camera pan offset     0.0
Camera tilt offset    0.0
Left motor trim       1.0
Right motor trim      1.0
Grayscale floor       None
Grayscale line        None
```

A missing calibration file is therefore not inherently an error.

It means the robot is using its default calibration.

## Persistence

Calibration is persisted by `CalibrationManager`.

The manager is responsible for:

- loading calibration
- saving calibration
- determining whether saved calibration exists
- resetting persisted calibration

Application code should normally use `CalibrationService` rather than
constructing replacement calibration documents manually.

## Calibration Service

`CalibrationService` provides application-level calibration operations.

Current operations include:

- load calibration
- save complete calibration
- update steering
- update camera mount
- update motor trim
- update grayscale calibration
- clear grayscale calibration
- reset all calibration

The service delegates persistence to `CalibrationManager`.

For example, a grayscale update conceptually follows:

```text
CalibrationService.update_grayscale(...)
             ↓
Construct GrayscaleCalibration
             ↓
Validate calibration
             ↓
Replace grayscale portion
             ↓
Save RobotCalibration
```

If the new calibration is invalid, it is rejected before being persisted.

## Calibration Models

Calibration models are immutable value objects.

They validate their own invariants so invalid calibration cannot be silently
stored.

This is important because browser validation alone is not sufficient.

A caller could bypass Launchpad and invoke application code directly.

Server-side calibration validity must therefore remain authoritative.

## Steering Calibration

Steering calibration records the offset required to make the robot's logical
center correspond to its physical straight-ahead position.

Conceptually:

```text
Logical steering center
          +
Steering calibration offset
          ↓
Physical servo position
```

A steering calibration preview temporarily applies the candidate offset and
centers the steering hardware so the user can inspect the result before
saving it.

## Camera Mount Calibration

Camera mount calibration stores:

- pan offset
- tilt offset

These values compensate for physical alignment differences in the pan/tilt
mount.

A camera calibration preview temporarily applies candidate offsets and centers
the mount.

The preview does not permanently change the runtime's current calibration.

## Motor Calibration

Motor calibration stores:

- left trim
- right trim

Motor trim compensates for differences in motor output so the robot can drive
more evenly.

Trim values are normalized to the supported motor-calibration range.

Motor preview is an active calibration operation because it physically drives
the robot.

The robot must be positioned safely before motor calibration is performed.

## Grayscale Calibration

Grayscale calibration stores two three-channel references:

```text
floor = (left, middle, right)
line  = (left, middle, right)
```

These references allow raw grayscale readings to be normalized relative to the
surfaces observed by the robot.

Both references must either be present or absent.

Valid:

```text
floor = None
line  = None
```

Valid:

```text
floor = (850, 870, 840)
line  = (1850, 1920, 1880)
```

Invalid:

```text
floor = (850, 870, 840)
line  = None
```

## Minimum Grayscale Separation

A valid grayscale calibration requires each floor/line channel pair to differ
by at least:

```text
100
```

For every channel:

```text
abs(floor[channel] - line[channel]) >= 100
```

All three channels must satisfy this rule.

For example:

```text
floor = (1000, 1000, 1000)
line  = (1100, 1250, 1400)
```

is valid.

But:

```text
floor = (1000, 1000, 1000)
line  = (1099, 1250, 1400)
```

is invalid because the first channel differs by only `99`.

## Why the Minimum Exists

Floor and line values that are identical cannot be normalized meaningfully.

Even values that differ by only a very small amount produce an unstable
calibration because minor sensor noise can dominate the normalized result.

The minimum span prevents configurations that are mathematically invalid or
too fragile for reliable line sensing.

This rule is part of calibration validity rather than only a Launchpad user
interface preference.

## Launchpad Grayscale Validation

Launchpad mirrors the minimum-separation rule so users receive immediate
feedback before attempting to save.

The page should:

- require both Floor and Line captures
- check all three channels
- disable Save when any channel differs by less than `100`
- explain why the captured references are invalid

Client-side validation improves usability.

The server-side calibration model remains authoritative.

## Grayscale Sensor Health vs. Calibration

Grayscale calibration and grayscale hardware health are different concepts.

```text
Hardware health
    → Can raw sensor readings be obtained?
    → Do those readings appear plausible?

Calibration
    → What raw values represent floor and line?
```

A grayscale module can be healthy but uncalibrated.

Likewise, valid saved calibration does not prove the sensor is currently
connected.

Platform health and calibration must remain separate.

## Clearing Grayscale Calibration

Grayscale calibration can be cleared without resetting the other calibration
areas.

Clearing it returns grayscale state to:

```text
floor = None
line  = None
```

Steering, camera, and motor calibration remain unchanged.

This is distinct from a full calibration reset.

## Calibration Hardware

Physical calibration operations are implemented through
`CalibrationHardware`.

`CalibrationHardware` does not directly own Robot HAT devices.

Instead, it communicates with the centralized robot runtime using
`RobotRuntimeClient`.

This keeps calibration inside the same hardware ownership model used by Manual
Drive and student programs.

## Control Ownership

Actuator calibration requires exclusive robot control.

Examples include:

- steering preview
- camera preview
- motor preview
- full calibration reset

If another application owns robot control, the calibration operation is
rejected as busy.

For example:

```text
Manual Drive owns control
        ↓
User attempts steering preview
        ↓
Calibration requests control
        ↓
Runtime rejects request as busy
```

Calibration must not bypass the runtime and independently construct actuator
hardware in response to a control conflict.

## Read-Only Calibration Operations

Grayscale sampling does not require actuator control.

The calibration hardware layer can request raw grayscale readings through the
runtime without taking the control lease.

This allows line-sensor calibration to coexist with the runtime's centralized
hardware ownership without unnecessarily blocking actuator control.

## Steering Preview

Steering preview follows this pattern:

```text
Acquire control
      ↓
Temporarily apply candidate offset
      ↓
Center steering
      ↓
Restore previous runtime offset
      ↓
Release control
```

The physical servo remains where the preview placed it, while the runtime's
stored in-memory offset returns to its previous value.

Saving the calibration is a separate operation.

## Camera Preview

Camera preview uses the same temporary-calibration pattern.

```text
Acquire control
      ↓
Temporarily apply candidate pan/tilt offsets
      ↓
Center camera mount
      ↓
Restore previous runtime offsets
      ↓
Release control
```

This lets the user inspect alignment before saving.

## Motor Preview

Motor preview is intentionally different because motor trim can only be
evaluated by physically driving the robot.

The preview:

- acquires control
- applies candidate motor trim
- uses the supplied steering calibration
- drives the robot briefly
- stops the motors
- restores the runtime's previous calibration state
- releases control

Motor preview must always stop the drive system even when an operation fails.

## Full Reset

The Calibration page provides a top-level Reset operation.

This is different from section-level Reset controls that merely discard
unsaved editor changes.

The full Reset restores the robot to its default uncalibrated state.

## Physical Reset Behavior

A full reset first returns actuator hardware to the positions associated with
the uncalibrated defaults.

The operation:

1. acquires robot control;
2. stops the drive motors;
3. centers steering using offset `0.0`;
4. centers camera pan using offset `0.0`;
5. centers camera tilt using offset `0.0`;
6. releases runtime control;
7. resets persisted calibration.

The motor trim values themselves do not require physical motion during reset.

The motors are simply stopped.

## Persisted Reset Behavior

After the physical reset succeeds, persisted calibration returns to:

```text
Steering offset       0.0
Camera pan offset     0.0
Camera tilt offset    0.0
Left motor trim       1.0
Right motor trim      1.0
Grayscale floor       None
Grayscale line        None
```

The result is equivalent to `RobotCalibration.default()`.

## Reset Ordering

Physical reset occurs before persisted calibration is cleared.

This ordering is deliberate.

Consider:

```text
Calibration file reset
        ↓
Attempt physical reset
        ↓
Robot control is busy
```

The robot would now have lost its saved calibration without having physically
returned to its default positions.

Instead the platform uses:

```text
Acquire control
        ↓
Physically reset robot
        ↓
Persist default calibration
```

If control cannot be acquired, the saved calibration remains unchanged.

## Reset and Busy Control

If Manual Drive, a student program, or another calibration operation currently
owns robot control, full Reset is rejected.

The user should receive a control-conflict message rather than a generic
hardware failure.

Once the existing owner releases control, Reset can be attempted again.

## Reset Recovery

Reset also serves as a recovery mechanism for invalid saved calibration.

The persisted reset operation does not need to successfully load the current
calibration first.

This is important if a malformed or historically invalid calibration file
prevents the normal Calibration page state from loading.

The top-level Reset control should therefore remain available when practical
even when loading the current calibration fails.

## Saving Calibration

Saving a calibration changes persisted robot state.

It should not be confused with previewing.

```text
Preview
    → physically test a candidate value
    → does not persist it

Save
    → validate candidate value
    → persist it
```

A user may preview several candidate values before choosing one to save.

## Runtime Calibration State

Calibration previews temporarily alter runtime-owned subsystem calibration for
the duration of the preview operation.

They then restore the previous runtime state.

Persisting a new calibration does not imply that every long-lived object in
every process automatically mutates immediately.

Applications should rely on the supported robot/runtime construction and
calibration-loading lifecycle rather than retaining undocumented assumptions
about stale calibration instances.

## Calibration Storage

Calibration storage is responsible for serializing the complete
`RobotCalibration` document.

Storage should reject:

- unsupported calibration versions
- malformed data
- invalid calibration values

A calibration file that exists but cannot be parsed or validated is different
from a missing calibration file.

Missing:

```text
Use RobotCalibration.default()
```

Invalid:

```text
Report calibration storage error
```

Invalid saved data must not silently become trusted robot configuration.

## Calibration Version

The calibration document includes a calibration format version.

The version allows future schema changes to be detected explicitly.

Unsupported calibration versions should be rejected rather than guessed at.

If the format changes in the future, migration behavior should be deliberate
and documented.

## Error Handling

Calibration operations can fail for different reasons.

### Invalid calibration

Examples:

- non-numeric value
- non-finite value
- incorrect number of grayscale channels
- grayscale floor without line
- grayscale line without floor
- grayscale span below `100`
- trim outside its supported range
- servo offset outside configured limits

These are validation errors.

### Robot busy

Another application owns actuator control.

This is a control conflict, not broken hardware.

### Runtime failure

The centralized runtime is unavailable or cannot complete a physical preview.

### Storage failure

Calibration could not be loaded, saved, removed, or otherwise persisted.

The user-facing interface should preserve these distinctions where practical.

## Launchpad Responsibilities

Launchpad provides the normal calibration workflow.

Its responsibilities include:

- displaying saved values
- maintaining unsaved editor state
- requesting hardware previews
- capturing grayscale references
- providing immediate validation feedback
- saving valid calibration
- clearing grayscale calibration
- resetting all calibration
- presenting errors

Launchpad is not the authoritative source of calibration validity.

Server-side models and services remain authoritative.

## Section Reset vs. Full Reset

The word Reset can refer to two different UI concepts.

### Section Reset

A section-level Reset discards unsaved edits for that section and restores the
editor to the currently saved values.

It does not alter persisted calibration.

### Full Reset

The top-level Reset restores all persisted robot calibration to the platform
defaults and physically returns supported actuators to their default
uncalibrated positions.

These behaviors should remain distinct even if the visible controls use
similar labels.

## User Safety

Calibration can physically move the robot.

Before actuator previews:

- place the robot on a clear surface
- keep hands away from moving mechanisms
- ensure the camera mount can move freely
- ensure motor preview has sufficient clear space

Motor preview is especially important because it intentionally drives the
robot.

The interface should make physical movement predictable rather than surprising.

## Calibration and Robot Configuration

Base robot configuration and calibration serve different purposes.

### Robot configuration

Describes the robot's designed hardware and operating constraints.

Examples:

- steering minimum angle
- steering maximum angle
- motor wiring
- sensor channels
- camera mount limits

### Calibration

Describes adjustments for one physical robot.

Examples:

- steering center offset
- camera alignment offset
- motor trim
- local floor/line references

Calibration must remain within limits defined by the robot configuration.

It should not be used to override fundamental hardware constraints.

## Calibration and Platform Health

Calibration validity can affect robot behavior, but calibration should not be
confused with passive health.

Examples:

```text
No grayscale calibration
    → valid uncalibrated state

Invalid grayscale calibration
    → configuration error

Grayscale sensor unavailable
    → hardware-health condition
```

These three states have different causes and should be represented
differently.

## Adding a Calibration Field

Before adding a new calibration value, determine:

1. What physical variation is being compensated for?
2. What is the safe default?
3. What type and range are valid?
4. Can the value be previewed safely?
5. Does preview require runtime control?
6. How is the value persisted?
7. How should reset behave?
8. Does old stored calibration remain compatible?
9. Does the runtime need a preview operation?
10. What automated and physical tests are required?

Calibration fields should not become arbitrary user-configurable robot
settings.

They should represent actual physical calibration.

## Testing

Calibration testing should cover the model, service, routes, and hardware
coordination separately.

### Model tests

Examples:

- default calibration
- valid values
- invalid values
- serialization
- deserialization
- calibration version handling
- grayscale both-set/both-empty invariant
- grayscale minimum separation

Grayscale boundary tests should include:

```text
difference = 0       reject
difference = 99      reject
difference = 100     accept
difference > 100     accept
one invalid channel  reject complete calibration
None / None          accept
```

### Service tests

Examples:

- update steering
- update camera
- update motors
- update grayscale
- clear grayscale
- reset
- failed validation does not modify saved calibration

### Route tests

Examples:

- valid update returns success
- invalid grayscale returns HTTP 400
- busy preview/reset returns HTTP 409
- reset returns default calibration
- storage failure is translated appropriately

### Runtime/calibration hardware tests

Examples:

- preview uses a control lease
- preview owner is descriptive
- busy control becomes `RobotBusyError`
- steering preview sends correct candidate offset
- camera preview sends correct offsets
- motor preview restores state and stops
- full reset stops drive and previews zero offsets

## Real-Hardware Validation

Automated tests cannot prove physical calibration quality.

Real-robot validation should verify:

### Steering

- preview visibly changes physical center
- saved offset is respected by normal robot use
- full Reset returns physical steering to uncalibrated center

### Camera

- pan preview aligns correctly
- tilt preview aligns correctly
- saved offsets are respected
- full Reset returns both axes to default center

### Motors

- motor preview drives safely
- trim changes affect relative motor output as expected
- motors stop after preview
- full Reset leaves motors stopped

### Grayscale

- Floor capture obtains three usable readings
- Line capture obtains three usable readings
- differences below `100` cannot be saved
- valid references can be saved
- clearing removes calibration
- full Reset returns grayscale to uncalibrated state

## Architectural Rules

The following rules should remain true as calibration evolves:

1. Calibration represents physical robot adjustment, not arbitrary settings.
2. Default calibration must always be safe and valid.
3. Missing calibration means use defaults.
4. Invalid calibration must not silently become trusted configuration.
5. Validation belongs in server-side calibration models or services.
6. Launchpad may mirror validation for immediate user feedback.
7. Actuator previews use the centralized runtime.
8. Calibration must not construct competing actuator hardware.
9. Read-only sensor sampling should not acquire actuator control unnecessarily.
10. Only one actuator calibration operation can own robot control at a time.
11. Preview and Save are separate operations.
12. Preview must restore runtime calibration state after testing a candidate.
13. Motor preview must leave the motors stopped.
14. Grayscale Floor and Line must both exist or both be absent.
15. Every grayscale floor/line channel must differ by at least `100`.
16. Grayscale calibration and grayscale hardware health are separate concepts.
17. Full Reset physically returns supported actuators to uncalibrated defaults.
18. Full Reset restores persisted `RobotCalibration.default()`.
19. Physical reset occurs before persisted reset.
20. A control conflict during reset must leave existing persisted calibration
    intact.

## Related Documentation

- [Platform Architecture](architecture.md)
- [Central Robot Runtime](runtime.md)
- [Betabox Launchpad](launchpad.md)
- [Platform Health and Diagnostics](platform-health.md)
- [Hardware](hardware.md)
- [Development](development.md)
