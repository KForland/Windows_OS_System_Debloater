Windows System Debloater

Windows System Debloater is a lightweight Windows utility that disables or restores selected non-essential Windows services and features using only native Windows mechanisms. It is designed to reduce background noise, ads, and unused services without breaking core system functionality.

The tool operates entirely through built-in Windows commands such as sc and reg. It does not delete files, install services, create scheduled tasks, or add persistence of any kind.

Administrator privileges are required. If the tool is not run with elevated permissions, it will exit immediately without making changes.

On launch, the user is presented with a dialog menu. Selecting YES applies a safe debloat configuration. Selecting NO restores only the services and registry values that this tool previously modified. Selecting CANCEL exits without making any changes.

When applying changes, the tool disables selected Windows services related to retail demo mode, offline maps, geolocation, remote registry access, fax services, media sharing, error reporting, NFC and wallet functionality, and phone integration. It also disables Windows Consumer Experience features that surface ads and suggestions, and turns off Xbox Game Bar automation and Game DVR capture functionality.

When restoring changes, the tool re-enables the same services and removes the registry values it previously set, returning the system to its prior state as closely as possible without touching unrelated settings.

After execution, a summary dialog is displayed showing which items were applied, which were restored, which were already compliant, and which actions failed. A system reboot is recommended after applying or restoring changes.

This tool is intentionally conservative. It does not modify Windows Update, Microsoft Defender, networking components, the Xbox app, Xbox Game Pass functionality, multiplayer services, or core system dependencies.

The tool makes no network connections and performs no telemetry of its own. It is suitable for personal systems, test environments, security labs, and demonstration purposes where a minimal and reversible debloat is desired.

Group Policy, enterprise management tools, or future Windows updates may override local changes made by this utility.

Use at your own risk. Review the source code before running.
