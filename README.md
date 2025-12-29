Windows System Debloater

Windows System Debloater is a lightweight Windows utility that disables or restores a small set of non-essential Windows services and features using only native Windows mechanisms. It is designed to reduce background noise, advertisements, and unused functionality without breaking core system behavior.

The tool operates entirely through built-in Windows commands such as sc and reg. It does not delete files, install services, create scheduled tasks, add startup persistence, or make network connections.

Administrator privileges are required. If the tool is not run with elevated permissions, it will exit immediately without making any changes.

On launch, the user is presented with a dialog menu:

YES applies a conservative debloat configuration

NO restores only the services and registry values modified by this tool

CANCEL exits without making changes

When applying changes, the tool disables selected Windows services related to:

Retail demo mode

Offline maps

Geolocation

Remote Registry access

Fax services

Media sharing

Error reporting

NFC, payments, and wallet functionality

Phone and messaging integration

It also applies policy-safe registry settings to:

Disable Windows Consumer Experience features that surface ads and suggestions

Disable Xbox Game Bar automation

Disable Game DVR background capture

When restoring changes, the tool re-enables the same services and removes only the registry values it previously set. It does not attempt to restore unrelated system settings or guess at defaults beyond what it explicitly changed.

After execution, a summary dialog is displayed showing:

Items that were applied

Items that were restored

Items already in the desired state

Any actions that failed

A system reboot is recommended after applying or restoring changes.

This tool is intentionally conservative. It does not modify:

Windows Update

Microsoft Defender

Networking components

The Xbox app or Xbox Game Pass

Multiplayer services

Core system dependencies

The tool performs no telemetry and leaves no background components running. It is suitable for personal systems, test environments, security labs, and demonstrations where a minimal, reversible debloat is desired.

Group Policy, enterprise management tools, or future Windows updates may override local changes made by this utility.

Use at your own risk. Review the source code before running.
