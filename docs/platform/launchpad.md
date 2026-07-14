# Betabox Launchpad

**Status:** Platform Architecture Specification\
**Project:** Betabox Robot Platform\
**Document:** `launchpad.md`

------------------------------------------------------------------------

## Purpose

Betabox Launchpad is the primary browser-based interface for interacting
with a Betabox robot.

Launchpad provides a student-friendly workspace for operating, coding,
and monitoring the robot while exposing additional administration and
recovery tools to teachers.

Rather than replacing the Betabox Robotics SDK or Platform Services,
Launchpad builds upon them to provide a unified classroom experience.

------------------------------------------------------------------------

## Philosophy

Launchpad is designed around several core principles.

-    Student-first user experience
-    Stable platform interfaces
-    Role-based access
-    Offline-first operation
-    Safe robot control
-    Reuse existing platform services
-    Simple classroom deployment

Launchpad should never duplicate platform logic. Instead, it should call
the same Robot API and Platform Services used by the command-line tools.

------------------------------------------------------------------------

## Platform Overview

``` text
                 Browser
                    │
                    ▼
            Betabox Launchpad
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
   Robot API             Platform Services
        │                        │
        └────────────┬───────────┘
                     ▼
              Betabox Platform
```

------------------------------------------------------------------------

## User Roles

### Student

Students interact with the robot but cannot modify the platform.

Student capabilities include:

-    Manual driving
-    Live camera
-    JupyterLab
-    Media browser
-    Robot status
-    Basic calibration

### Teacher

Teachers inherit all student capabilities and gain access to platform
management tools.

Additional capabilities include:

-    Diagnostics
-    Verification
-    Doctor
-    Logs
-    Events
-    Backup
-    Restore
-    Reset
-    Service management
-    Advanced calibration
-    Platform configuration

Authorization must always be enforced by the backend.

------------------------------------------------------------------------

## Major Components

### Home

The Launchpad landing page provides entry points to all available tools.

### Manual Drive

Provides browser-based robot control with live video, steering, speed,
and emergency stop functionality.

Only one controller may operate the robot at a time.

### JupyterLab

Provides access to the classroom coding environment.

### Media Browser

Provides access to pictures, videos, and sounds created by the robot.

### Robot Status

Displays robot health, battery status, sensor information, and platform
status.

### Diagnostics

Provides access to Verify, Doctor, logs, events, and health reporting.

### Recovery

Provides teacher-only backup, restore, reset, and diagnostic snapshot
tools.

------------------------------------------------------------------------

## Responsibilities

Launchpad is responsible for:

-    Providing a browser-based user experience
-    Enforcing role-based access
-    Presenting robot information
-    Presenting platform diagnostics
-    Providing safe manual robot control
-    Linking users to the coding environment

------------------------------------------------------------------------

## Non-Responsibilities

Launchpad is **not** responsible for:

-    Hardware control implementations
-    Robot algorithms
-    Platform diagnostics
-    Service management logic
-    Backup implementation
-    Recovery implementation

------------------------------------------------------------------------

## Design Goals

-    Student-first interface
-    Consistent teacher workflow
-    Safe robot control
-    Responsive browser experience
-    Offline classroom operation
-    Minimal duplication of platform logic
-    Long-term maintainability

------------------------------------------------------------------------

## Initial Release

The first Launchpad release will include:

-    Home dashboard
-    Student and teacher modes
-    Robot status
-    Manual driving
-    JupyterLab link
-    Live video
-    Media browser
-    Teacher diagnostics

------------------------------------------------------------------------

## Future Direction

Future Launchpad capabilities may include:

-    Teacher Portal integration
-    Student Portal integration
-    Classroom management
-    Fleet management
-    Curriculum integration
-    AI-assisted troubleshooting
-    Remote administration

------------------------------------------------------------------------

## Summary

Betabox Launchpad is the browser-based front end for the Betabox
Platform. It builds upon the stable Robot API and Platform Services to
provide a unified, student-friendly classroom experience while exposing
powerful administration and recovery capabilities to teachers.
