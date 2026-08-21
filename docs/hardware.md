# Hardware

Betabox Robotics provides reusable Python abstractions for the physical
hardware used by the Betabox robotic car.

The hardware layer is the lowest software layer of the robot platform.

It provides access to individual hardware resources and devices without
containing classroom application behavior, robot-level policy, or Launchpad
logic.

Normal applications should use the high-level Robot API or centralized robot
runtime rather than constructing hardware devices directly.

## Purpose

The hardware layer provides reusable interfaces for physical components such
as:

- digital pins
- analog channels
- PWM channels
- I2C
- ADC inputs
- PWM outputs
- servos
- DC motors

These abstractions are then composed into higher-level robot subsystems.

Conceptually:

```text
Applications
     │
     ▼
Public Robot API
     │
     ▼
Central Robot Runtime
     │
     ▼
Configured Robot
     │
     ├── Drive
     ├── Sensors
     └── Camera Mount
             │
             ▼
         Hardware Layer
             │
             ▼
      Physical Hardware
```

The hardware layer should remain reusable independently of any one application.

## Layering

Betabox follows a layered hardware architecture.

```text
Physical interfaces
        ↓
Hardware abstractions
        ↓
Reusable devices
        ↓
Robot subsystems
        ↓
Configured robot
        ↓
Central runtime
        ↓
Applications
```

Each layer has a different responsibility.

### Physical interfaces

Represent hardware resources such as:

- GPIO
- ADC channels
- PWM channels
- I2C

### Hardware abstractions

Provide validated Python interfaces to those resources.

### Devices

Represent reusable physical devices such as:

- PWM outputs
- servos
- motors

### Subsystems

Combine devices into robot capabilities such as:

- drive
- steering
- grayscale sensing
- ultrasonic sensing
- battery sensing
- camera mount

### Robot

Combines configured subsystems into a complete Betabox car.

### Runtime

Owns the long-lived robot instance and coordinates shared access.

### Applications

Use supported high-level interfaces rather than competing for physical
resources.

## Hardware Package

Low-level hardware functionality lives under the Betabox Robotics hardware
package.

The exact module structure may evolve, but the package contains abstractions
for areas such as:

```text
hardware/
    board
    pin
    i2c
    adc
    pwm
    servo
    motor
```

Applications should depend on the public hardware interfaces rather than
implementation details where possible.

## Board Mapping

The board layer describes the named physical resources available through the
supported Robot HAT.

This includes mappings for resources such as:

```text
D0 ... D7
A0 ... A7
PWM channels
```

Named resources allow higher layers to describe robot wiring without
scattering raw hardware identifiers throughout the codebase.

For example:

```text
Robot configuration
       ↓
Named board resource
       ↓
Hardware abstraction
       ↓
Physical channel
```

The board mapping should describe hardware identity.

It should not contain robot behavior.

## Digital Pins

Digital pins represent GPIO-style digital resources.

They support the operations required by devices and sensors that use digital
signals.

Pin abstractions are responsible for concerns such as:

- pin identity
- mode
- pull configuration
- digital input
- digital output
- edge/trigger behavior where supported
- validation
- cleanup

Higher-level code should not need to reproduce low-level pin configuration
rules.

## Pin Modes

Digital pins may operate in modes appropriate to their physical use.

Examples include:

```text
input
output
```

Additional supported pin behavior is represented through the hardware API
rather than arbitrary string values.

Invalid modes or unsupported operations should produce explicit hardware
errors rather than silently doing nothing.

## Pull Configuration

Input pins may support pull configuration such as:

```text
up
down
none
```

Pull behavior belongs to the pin abstraction because it is part of the
electrical interface, not robot-level behavior.

## Analog Channels

Analog channels identify ADC inputs available to the robot.

The board exposes named analog resources such as:

```text
A0
A1
A2
...
A7
```

An analog channel identifies where a measurement comes from.

The ADC abstraction is responsible for obtaining the actual reading.

## ADC

The ADC layer provides access to analog sensor values.

ADC readings are used by higher-level sensors such as:

- grayscale
- battery monitoring

Raw ADC values are hardware measurements.

Their meaning belongs to the subsystem using them.

For example:

```text
ADC value
    ↓
Battery subsystem
    ↓
Voltage conversion
    ↓
Battery state
```

or:

```text
ADC values
    ↓
Grayscale subsystem
    ↓
Raw grayscale readings
    ↓
Calibration / line interpretation
```

The ADC layer should not decide whether a battery is low or whether a
grayscale sensor sees a line.

## PWM Channels

PWM channels identify hardware PWM resources.

A PWM channel represents the physical channel used by a PWM-controlled device.

Higher-level PWM, servo, and motor abstractions build on these resources.

## PWM

The PWM abstraction provides controlled pulse-width modulation.

PWM is used as a building block for devices such as:

- servos
- motors

The PWM layer is responsible for translating validated software requests into
the supported low-level PWM behavior.

It should not contain steering, drive, or camera-specific policy.

## Servo

`Servo` represents a reusable servo device.

A servo abstraction is responsible for operations such as:

- positioning
- validating supported values
- translating requested position into PWM behavior
- hardware cleanup

A generic servo does not know whether it is being used for:

- steering
- camera pan
- camera tilt
- another mechanism

That meaning is supplied by the subsystem and robot configuration.

Conceptually:

```text
Steering subsystem
       ↓
Servo
       ↓
PWM
       ↓
Physical steering servo
```

and:

```text
Camera mount
       ↓
Servo
       ↓
PWM
       ↓
Physical pan/tilt servo
```

## Motor

`Motor` represents a reusable DC motor interface.

The motor abstraction handles the low-level control required for a configured
motor.

Motor behavior may include:

- forward output
- reverse output
- stopping
- direction handling
- output scaling
- hardware validation

Robot-specific concerns such as:

- left vs. right motor
- trim
- steering interaction
- driving straight
- robot movement

belong above the generic motor layer.

## Motor Direction

Physical motor wiring may require one motor to be logically reversed relative
to another.

That wiring difference should be represented through configuration rather than
duplicating movement logic throughout the application.

Conceptually:

```text
Requested forward
      ↓
Drive subsystem
      ↓
Motor configuration
      ↓
Correct physical direction
```

The public robot API should not need to know the electrical orientation of an
individual motor.

## Motor Trim

Motor trim is calibration rather than fundamental motor behavior.

The generic motor abstraction provides output control.

The robot's motor calibration determines how commanded output is adjusted for
the physical differences between the left and right motors.

This distinction keeps:

```text
Hardware capability
```

separate from:

```text
Individual robot calibration
```

See [Calibration](calibration.md).

## I2C

The I2C abstraction provides communication with supported I2C devices.

It is responsible for low-level operations such as:

- device addressing
- reads
- writes
- communication errors
- retry behavior

Higher layers should not duplicate I2C retry or error-handling policy.

## I2C Errors

I2C communication can fail for reasons such as:

- device unavailable
- Robot HAT powered off
- wiring problem
- bus error
- temporary communication failure

These conditions should produce meaningful hardware errors.

Higher layers can then interpret the failure according to context.

For example:

```text
I2C failure
    ↓
Passive hardware check
    ↓
Robot HAT unavailable
    ↓
Platform health warning/error
```

The I2C layer itself should not decide overall platform health.

## Hardware Exceptions

The hardware layer uses explicit exceptions for invalid operations and
hardware failures.

Examples include errors representing conditions such as:

- invalid pin
- invalid mode
- pin configuration failure
- I2C failure
- PWM failure
- servo failure
- motor failure

Callers should catch errors they can meaningfully handle.

Avoid broad exception handling that hides programming errors or unrelated
failures.

For example:

```python
try:
    ...
except MotorError:
    ...
```

is preferable when the caller specifically knows how to handle a motor
failure.

## Validation

Hardware APIs validate their inputs at the layer where the constraint belongs.

Examples include:

- valid pin identifiers
- valid modes
- valid channel identifiers
- finite numeric values
- supported PWM values
- supported servo ranges
- supported motor values

Invalid input should fail explicitly rather than being silently coerced into
an unrelated hardware operation.

## Hardware Configuration

Generic hardware abstractions should not hard-code the complete Betabox robot
wiring.

Robot wiring belongs to robot configuration.

Conceptually:

```text
Generic Motor
Generic Servo
Generic ADC
       │
       ▼
Robot Configuration
       │
       ▼
Configured Subsystems
       │
       ▼
Betabox Car
```

This allows the low-level abstractions to remain reusable.

## Robot Configuration

The Betabox car configuration defines how reusable components are assembled
into the physical robot.

Configuration includes areas such as:

- motor wiring
- motor direction
- steering configuration
- steering limits
- ultrasonic configuration
- grayscale channels
- battery configuration
- camera mount configuration
- audio configuration
- vision configuration

The current standard Betabox car configuration is represented by the platform's
Betabox car configuration object.

Applications should not reproduce these values independently.

## Factory Pattern

Configured components and subsystems may expose factories that construct the
appropriate hardware from robot configuration.

Conceptually:

```python
component = Component.default(config)
```

This pattern allows:

```text
Generic implementation
        +
Robot-specific configuration
        ↓
Configured component
```

Low-level hardware classes should remain usable without requiring the entire
Betabox robot configuration.

## Drive Hardware

The drive subsystem composes:

- left motor
- right motor
- steering servo

The subsystem adds robot-level behavior such as:

- forward
- backward
- stop
- steering
- steering limits
- motor trim
- steering calibration

Applications should use the drive subsystem, Robot API, or runtime rather than
coordinating the individual motors themselves.

## Steering

Steering is implemented using a servo but is not merely a generic servo from
the application's perspective.

The steering layer adds:

- configured angle limits
- logical steering behavior
- center
- calibration offset

Conceptually:

```text
Requested steering angle
         ↓
Steering limits
         ↓
Calibration offset
         ↓
Servo command
```

The generic servo remains unaware of steering semantics.

## Camera Mount

The camera mount uses servo hardware for:

- pan
- tilt

The camera mount applies:

- configured physical limits
- calibration offsets
- logical centering behavior

Camera mount control is separate from camera image capture.

```text
Camera mount servos
        ↓
Robot Runtime

Camera sensor
        ↓
Vision Service
```

This distinction prevents camera streaming and physical camera movement from
becoming unnecessarily coupled.

## Grayscale Hardware

The grayscale module provides three analog sensor readings:

```text
left
middle
right
```

The subsystem reads these values through configured ADC channels.

Raw readings are then available for:

- sensor status
- calibration
- line sensing
- student programs

The hardware layer does not decide what constitutes floor or line.

Those interpretations belong to calibration and sensor behavior above the ADC
layer.

## Grayscale Plausibility

Platform health may evaluate whether grayscale readings appear physically
plausible.

That evaluation is not part of the ADC hardware abstraction.

The distinction is:

```text
ADC
    → returns raw value

Grayscale subsystem
    → identifies three sensor readings

Health system
    → determines whether readings appear suspicious

Calibration
    → determines floor/line references
```

Keeping these responsibilities separate prevents health heuristics from
leaking into generic hardware code.

## Ultrasonic Hardware

The ultrasonic subsystem uses configured hardware resources to obtain distance
measurements.

It provides a reusable sensor API above the raw pin behavior required by the
physical sensor.

Applications should consume the ultrasonic subsystem or high-level Robot API
rather than manually reproducing trigger/echo timing.

Ultrasonic readings are also available through the centralized runtime for
shared read-only access.

## Battery Hardware

Battery monitoring uses an analog input and configured conversion behavior to
estimate robot battery voltage.

Conceptually:

```text
ADC reading
     ↓
Configured voltage conversion
     ↓
Battery voltage
     ↓
Battery state
```

Voltage conversion belongs to the battery subsystem.

Battery-health classification belongs to the appropriate sensor/platform
health layer.

The ADC abstraction should remain unaware of battery thresholds.

## Vision Hardware

The physical camera is intentionally not treated like ordinary
runtime-owned hardware.

Normal camera capture is owned by the shared vision service.

```text
Physical camera
      ↓
Camera manager / frame source
      ↓
Vision service
      ↓
Consumers
```

This prevents multiple processes from independently attempting to own the same
camera.

Applications needing frames should use the supported vision interfaces rather
than opening another Picamera2 instance.

## Audio Hardware

Audio has its own subsystem and hardware path.

The audio system may involve:

- configured audio output hardware
- amplifier enable control
- speech backends
- playback backends

Audio is not treated as ordinary robot actuator control under the centralized
runtime lease.

This allows audio playback to remain independent from drive/servo ownership.

The ability to initialize or command the audio stack does not prove that
audible sound physically came from the speaker.

Physical audio validation therefore requires listening to the output.

## Physical Betabox Hardware

A normal Betabox car contains hardware including:

- Raspberry Pi
- Robot HAT
- two DC drive motors
- steering servo
- camera pan servo
- camera tilt servo
- Raspberry Pi camera
- ultrasonic distance sensor
- three-channel grayscale module
- battery
- audio output hardware
- speaker

Exact component revisions may evolve without changing the overall software
architecture.

## Raspberry Pi

The Raspberry Pi is the primary computer for the Betabox.

It runs:

- Raspberry Pi OS
- Betabox Robotics
- the centralized robot runtime
- Launchpad
- JupyterHub
- vision services
- monitoring
- supporting platform services

The Raspberry Pi communicates with the Robot HAT and directly or indirectly
with the other attached hardware.

## Robot HAT

The Robot HAT provides the primary interface between the Raspberry Pi and much
of the robot hardware.

It exposes resources used for areas such as:

- PWM
- ADC
- motor control
- servo control
- digital I/O

Availability of the Robot HAT is therefore an important platform-health
condition.

However:

```text
Robot HAT available
```

does not mean:

```text
Every attached physical component is working
```

The platform should preserve that distinction.

## Hardware Ownership

A physical resource should normally have one software owner.

For the composed robot hardware, that owner is the centralized robot runtime.

```text
Application A ─┐
Application B ─┼── Runtime ── Robot Hardware
Application C ─┘
```

Not:

```text
Application A ── Robot Hardware
Application B ── Robot Hardware
Application C ── Robot Hardware
```

Central ownership prevents competing initialization, conflicting commands, and
unsafe cleanup.

## Runtime Ownership

The runtime owns the long-lived configured robot hardware.

Applications own control sessions rather than the hardware itself.

This means:

```text
Application starts
    ≠
Hardware constructed

Application exits
    ≠
Hardware destroyed
```

The runtime establishes and maintains the hardware lifetime independently of
individual browser sessions, notebooks, or calibration operations.

See [Central Robot Runtime](runtime.md).

## Control Ownership

Runtime hardware ownership and actuator control ownership are different.

The runtime always owns the hardware.

One application at a time may own actuator control.

```text
Runtime
    └── owns hardware continuously

Manual Drive
    └── temporarily owns actuator control
```

When Manual Drive releases control, the runtime still owns the physical
hardware.

Another application may then acquire control without reconstructing the robot.

## Read-Only Hardware Access

Supported sensor reads do not require actuator control.

This allows applications such as:

- monitoring
- Status
- Diagnostics
- calibration sampling

to observe supported hardware while another application controls the robot.

Examples include:

- battery
- grayscale
- ultrasonic

Read-only access should still go through the runtime or shared platform
services rather than creating competing hardware instances.

## Direct Hardware Access

Direct hardware construction is appropriate primarily for:

- hardware-layer development
- isolated hardware validation
- low-level tests
- debugging a specific device

It is generally not appropriate for:

- Launchpad
- normal student programs
- platform monitoring
- platform diagnostics
- calibration actuator previews
- ordinary CLI operations

Those applications should use the established higher-level interfaces.

## Why Direct Access Is Dangerous

Bypassing centralized ownership can cause:

- GPIO conflicts
- PWM conflicts
- I2C conflicts
- competing servo commands
- competing motor commands
- hardware reinitialization
- unexpected cleanup
- runtime state becoming inaccurate

For example:

```text
Robot Runtime
     ↓
owns steering servo

Separate process
     ↓
constructs steering servo directly
```

creates two software owners for one physical resource.

That is an architecture violation even if it appears to work temporarily.

## Hardware Initialization

Hardware initialization should occur at the layer responsible for ownership.

For the normal running platform:

```text
Runtime service starts
        ↓
Configured robot constructed
        ↓
Hardware initialized
        ↓
Runtime ready
```

Launchpad opening a page should not initialize the entire robot.

Likewise, opening a notebook should not force unrelated platform hardware to be
destroyed and recreated.

## Hardware Cleanup

The component that owns hardware is responsible for final cleanup.

For the normal platform, the runtime owns the robot hardware lifetime and is
therefore responsible for final robot cleanup.

Individual runtime clients should release their control sessions.

They should not globally close hardware owned by the runtime.

Conceptually:

```text
Client disconnects
       ↓
Release control
       ↓
Runtime keeps hardware alive
```

At runtime shutdown:

```text
Runtime stops
      ↓
Actuators made safe
      ↓
Hardware closed
```

## Safe Actuator State

Actuator-owning code must consider what happens when:

- an operation completes
- control is released
- a client disconnects
- an exception occurs
- the runtime shuts down

Drive motors must not remain running because a client disappeared.

Physical movement operations should define their cleanup behavior explicitly.

## Hardware Health

Hardware availability and hardware functionality are not always directly
observable.

The platform therefore distinguishes between hardware it can passively inspect
and hardware requiring active validation.

## Passively Observable Hardware

The platform can obtain useful feedback from areas such as:

- Robot HAT / I2C communication
- battery
- grayscale sensor
- ultrasonic sensor
- camera through the vision service

These can participate in continuous health monitoring.

## Actuator Hardware Without Feedback

Current actuator hardware does not provide sufficient independent feedback to
prove physical motion.

This includes:

- drive motors
- steering servo
- camera pan servo
- camera tilt servo

The software can know:

```text
Command accepted
```

but not necessarily:

```text
Physical mechanism moved correctly
```

without additional feedback hardware.

## Audio Verification

Audio has a similar limitation.

The software can verify portions of the configured audio path and can issue
speech or playback operations.

It cannot passively prove:

```text
Speaker produced audible sound
```

That requires active physical validation.

## Hardware Validation

Hardware validation tests should deliberately exercise individual hardware
abstractions or physical devices.

Examples include:

- ADC reading
- PWM output
- servo movement
- motor movement
- ultrasonic reading
- grayscale reading
- camera capture
- audible output

These tests are different from normal continuous health monitoring.

## Validation Layers

Betabox distinguishes several forms of validation.

### Hardware validation

Tests an individual hardware abstraction or physical device.

Examples:

```text
Can this servo move?
Can this ADC channel be read?
Can this motor turn?
```

### Subsystem validation

Tests a reusable configured subsystem.

Examples:

```text
Can Drive move and steer correctly?
Can Sensors return expected readings?
Can the camera mount pan and tilt?
```

### Robot validation

Tests the composed robot platform.

Examples:

```text
Can the complete configured Betabox car perform its supported operations?
```

### Platform health

Observes the running platform without unexpectedly actuating it.

These layers should not be conflated.

## Hardware Errors vs. Busy Errors

A hardware failure and a control conflict are different conditions.

For example:

```text
Motor hardware operation failed
```

is a hardware problem.

But:

```text
Launchpad Manual Drive currently owns control
```

when Calibration requests the robot is an ownership conflict.

Higher layers should not report `RobotBusyError` as broken hardware.

## Hardware Errors vs. Calibration Errors

Calibration also represents a separate class of problem.

For example:

```text
Grayscale sensor unavailable
```

is a hardware-health condition.

```text
Grayscale floor and line differ by less than 100
```

is a calibration-validation condition.

A physically healthy sensor can have invalid calibration.

A correctly calibrated sensor can later become physically unavailable.

## Hardware Errors vs. Configuration Errors

Configuration describes how the robot is expected to be wired.

A mismatch between configuration and physical hardware may appear as a
hardware failure, but the root cause can be configuration.

Troubleshooting should therefore consider:

```text
Hardware
Configuration
Calibration
Ownership
```

as separate possible causes.

## Adding Hardware Support

When adding a new hardware component, determine where each responsibility
belongs.

Ask:

1. What physical interface does the component use?
2. Does an existing hardware abstraction already represent that interface?
3. Is a new reusable device abstraction required?
4. Which subsystem owns the device?
5. How is its wiring represented in robot configuration?
6. Does it require centralized runtime ownership?
7. Is access read-only or actuator-controlling?
8. Can its physical state be passively verified?
9. What errors can it produce?
10. What cleanup is required?
11. Does it require calibration?
12. Should platform health monitor it?

Avoid adding device-specific behavior directly to Launchpad or the public Robot
API when a lower reusable layer is appropriate.

## Testing

Hardware tests should focus on the contract of each abstraction.

Important areas include:

- validation
- configuration
- state
- command translation
- expected hardware errors
- cleanup
- context-manager behavior where supported
- retry behavior
- boundary values

Tests should avoid requiring real hardware unless they are explicitly hardware
validation tests.

Software unit tests and physical validation serve different purposes.

## Mocked Tests

Automated unit tests can verify behavior such as:

- invalid pin rejection
- mode validation
- I2C retry behavior
- PWM command translation
- servo range handling
- motor direction handling
- cleanup calls

These tests verify software behavior.

They do not prove the physical hardware works.

## Real-Hardware Tests

Changes affecting hardware behavior should be validated on an actual Betabox.

Depending on the component, verify:

### Robot HAT

- expected I2C communication is available
- required channels can be accessed

### Motors

- left motor turns
- right motor turns
- forward direction is correct
- reverse direction is correct
- stop reliably stops both motors

### Steering

- servo moves
- configured limits are respected
- center behaves correctly

### Camera Mount

- pan moves correctly
- tilt moves correctly
- configured limits are respected

### Grayscale

- all three channels produce readings
- readings change appropriately over different surfaces

### Ultrasonic

- distance readings can be obtained
- readings respond to changes in obstacle distance

### Camera

- vision service can acquire frames
- usable frames reach consumers

### Audio

- playback is actually audible

Physical validation should be performed safely and with enough space for any
expected movement.

## Hardware Troubleshooting

When hardware appears unavailable, identify the layer at which the failure
occurs.

Conceptually:

```text
Physical device
      ↓
Electrical connection
      ↓
Hardware interface
      ↓
Hardware abstraction
      ↓
Subsystem
      ↓
Runtime
      ↓
Application
```

A failure visible in Launchpad does not necessarily mean Launchpad itself is
the source of the problem.

Useful platform tools include:

```bash
betabox status
betabox doctor
betabox events
```

Service state can be inspected with:

```bash
betabox services
```

See [Platform Health and Diagnostics](platform-health.md) for the platform-wide
troubleshooting model.

## Architectural Rules

The following rules should remain true as hardware support evolves:

1. The hardware layer contains reusable physical hardware abstractions.
2. Generic hardware classes should not contain Betabox application policy.
3. Robot wiring belongs in configuration rather than being scattered through
   applications.
4. Devices compose into subsystems before becoming robot-level behavior.
5. Normal applications use the public Robot API or centralized runtime.
6. The centralized runtime owns the long-lived composed robot hardware.
7. Applications own control sessions, not physical robot hardware.
8. Only one application owns actuator control at a time.
9. Supported read-only sensor access should not require actuator control.
10. Applications must not bypass runtime ownership to resolve control
    conflicts.
11. The vision service owns normal camera capture.
12. The runtime owns camera-mount servo control.
13. Audio remains separate from normal actuator-control ownership.
14. Calibration is separate from generic hardware behavior.
15. Platform health is separate from generic hardware behavior.
16. Hardware availability must not be confused with proof of physical
    functionality.
17. Actuators without feedback cannot be passively verified as mechanically
    working.
18. Hardware cleanup belongs to the component that owns the hardware lifetime.
19. Client disconnection must not destroy runtime-owned hardware.
20. New hardware should be introduced at the lowest appropriate reusable
    layer.

## Related Documentation

- [Platform Architecture](architecture.md)
- [Central Robot Runtime](runtime.md)
- [Platform Health and Diagnostics](platform-health.md)
- [Calibration](calibration.md)
- [Betabox Launchpad](launchpad.md)
- [Installation](installation.md)
- [Development](development.md)
