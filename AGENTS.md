There is nothing setup yet for this repo. Please start this project:

SpiritBox™ is a stateless, transient, secure extraction and containment service for isolating malware or other files directly on endpoints in real time. Designed for ultra-fast containment and absolute zero-trust file handling, SpiritBox monitors for specified file hashes (and/or a folder path) and instantly extracts that suspicious file (or files) into a nested container. From there, professionals can safely inspect the file in a hardened shell environment with minimal to no risk of compromise. SpiritBox is also auto-ephemral by design. Once analysis is completed, SpiritBox auto-deletes itself (containers, files, scripts, exes, everything) and leaves only a single log file ("sbox-log.txt"), leaving little traces of it ever existing.

As infrastructure, Spirit box runs entirely in memory and is two nested docker containers: The inner container called "detonation container" and the outer container "analysis container". Both containers are on their own docker network and volumes and only the analysis container is allowed inbound to the detonation container on port 22/SSH, that's it. The detonation container is what's built first as extraction of the specified file (or files if possible, but lets focus on single file extraction at this time) needs to be completed as quickly as possible. Denotation container is READ ONLY, extremely lightweight and -only- holds what is needed to succesfully extract that file successfully and allow SSH access from another container. We want all dependencies/libraries of the detonation container to be loaded and ready before Spirit Box is "ready to extract" the targeted file. 

Here is how we want spirit box to work start to finish as a console based app: 

1. User opens SpiritBox exe or script (Windows/Mac/Linux) - console window pops up (cli agent) with a nice ASCII label on the top half showing SpiritBox label and realtime status notice, the bottom half will be the console. The top half console "banner" status will show real time notices like "Building spiritbox" and eventually "Ready for instruction" and then "Ready for extraction" when it's setup it ready to pull a file the user has defined. The 

2. Wegeb 

# AGENTS.md - SpiritBox™ Agent Manifest

This document outlines the ROUGH core agents and microservices that power **SpiritBox™** — the stateless containment utility by Exoterik Labs™. Each agent operates independently in ephemeral runtime containers, working under strict security constraints to ensure zero trust and zero persistence.

---

## id: monitoring_agent
title: File Monitoring & Event Trigger Agent
type: Passive
description: >
  Monitors the specified directory for file creation events, and matches each file against a defined SHA-256 hash. When a match is found, it triggers containment procedures.
responsibilities:
  - Watch target folder for new file events
  - Validate file hash against target
  - Ensure minimal latency on match detection
  - Trigger containment_agent on match
health_states:
  - healthy: Actively watching and responsive
  - degraded: Inotify/FSEvents error or delay detected
  - fault: Watch path inaccessible or hash misconfigured

---

## id: containment_agent
title: Secure Virtualization & Capture Agent
type: Ephemeral
description: >
  Immediately encapsulates matching files into a hardened Docker or Podman container with restricted I/O, no network access, and quantum-safe encrypted storage. Creates a tamper-proof shell around the threat.
responsibilities:
  - Create secure inner container for the file
  - Isolate file from host and all subsystems
  - Apply filesystem ACLs and read-only mount
  - Store file in tmpfs or encrypted volume
health_states:
  - healthy: Container created and file stored safely
  - warning: Container initialized but encryption failed
  - fault: File failed to lock or container failed to start

---

## id: heuristic_agent
title: Anomaly Detection & Behavior Monitor
type: Behavioral
description: >
  Observes the runtime behavior of the contained file to identify signs of tampering, execution attempts, or suspicious patterns. Automatically terminates the container if threat thresholds are exceeded.
responsibilities:
  - Monitor syscalls and memory access
  - Detect sandbox escapes or unusual behavior
  - Auto-shutdown inner container on breach
  - Feed behavior log to logging_agent
health_states:
  - healthy: Monitoring actively with no anomalies
  - alert: Suspicious behavior detected
  - fault: Breach or breakout detected — container destroyed

---

## id: logging_agent
title: Forensic Logging & Report Generator
type: Immutable
description: >
  Generates encrypted, tamper-evident forensic logs for each session. Logs can be exported securely for offline review and saved alongside audit trails.
responsibilities:
  - Record hash, time, actions, and alerts
  - Encrypt logs with analyst key or session key
  - Optionally sign report with PGP key
  - Export logs to `/logs/.spiritlog.enc`
health_states:
  - healthy: Logging to memory and disk
  - degraded: Log encryption failed
  - fault: Log output could not be created or written

---

## id: cleanup_agent
title: Ephemeral Cleanup & Self-Destruct Handler
type: Auto
description: >
  Destroys all runtime containers, memory state, temporary files, and decrypted assets after each session. Ensures zero trace is left on host system after analysis.
responsibilities:
  - Stop and delete inner/outer containers
  - Wipe any decrypted tmpfs volumes
  - Securely shred session keys
  - Confirm deletion and exit cleanly
health_states:
  - healthy: Self-destruct succeeded
  - warning: Partial container or tmpfs cleanup
  - fault: Destruction routine failed or incomplete

---

## id: cli_agent
title: SpiritBox Console Interface
type: Interactive
description: >
  Provides a terminal-based menu interface for configuration, monitoring, and launching analysis tools. Enables command-line workflows for analysts without GUI dependency.
responsibilities:
  - Display console menu and banners
  - Accept input for folder/hash/config
  - Launch agents in sequence
  - Report agent statuses to user
health_states:
  - healthy: CLI menu functional and accepting input
  - degraded: Input timeout or subprocess failed
  - fault: Menu failed to initialize or crashed

---

## id: analysis_agent
title: On-Container Static & Signature Scanning
type: Optional
description: >
  Offers built-in scanning tools (ClamAV, YARA, entropy checks) inside the outer container to help analysts review the file without detonation. Fully air-gapped.
responsibilities:
  - Launch ClamAV scan on contained file
  - Run YARA rulesets
  - Flag suspicious binaries or patterns
  - Prepare exportable scan summary
health_states:
  - healthy: Scanners operational
  - degraded: Signature update failed or scan incomplete
  - fault: Tools failed to initialize or crash on scan

---

## Agent Lifecycle Overview

```plaintext

                 ┌────────────────────┐
                 │     cli_agent      │
                 └────────┬───────────┘               
                          │ 
                          ▼
                 ┌────────────────────┐
                 │  monitoring_agent  │
                 └────────┬───────────┘
                          │ file path hash match
                          ▼
                 ┌────────────────────┐
                 │ containment_agent  │◄───┐
                 └────────┬───────────┘    │
                          │ starts         │
                          ▼                │
                 ┌────────────────────┐    │
                 │ heuristic_agent    │────┘
                 └────────┬───────────┘
                          │ logs
                          ▼
                 ┌────────────────────┐
                 │  logging_agent     │
                 └────────┬───────────┘
                          │ complete
                          ▼
                 ┌────────────────────┐
                 │ cleanup_agent      │
                 └────────────────────┘
