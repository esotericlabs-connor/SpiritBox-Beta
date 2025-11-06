There is nothing setup yet for this repo. Please start this project:

SpiritBox™ is a stateless, transient, secure extraction and containment service for isolating malware or other files directly on endpoints in real time. Designed for ultra-fast containment and absolute zero-trust file handling, SpiritBox monitors for specified file hashes (and/or a folder path) and instantly extracts that suspicious file (or files) into a nested container. From there, professionals can safely inspect the file in a hardened shell environment with minimal to no risk of compromise. SpiritBox is also auto-ephemral by design. Once analysis is completed, SpiritBox auto-deletes itself (containers, files, scripts, exes, everything) and leaves only a single log file ("sbox-log.txt"), leaving little traces of it ever existing.

As infrastructure, Spirit box runs entirely in memory and is two nested docker containers: The inner container called "detonation container" and the outer container "analysis container". Both containers are on their own docker network and volumes and only the analysis container is allowed inbound to the detonation container on port 22/SSH, that's it. The detonation container is what's built first as extraction of the specified file (or files if possible, but lets focus on single file extraction at this time) needs to be completed as quickly as possible. Denotation container is READ ONLY, extremely lightweight and -only- holds what is needed to succesfully extract that file successfully and allow SSH access from another container. We want all dependencies/libraries of the detonation container to be loaded and ready before Spirit Box is "ready to extract" the targeted file. 

Here is how we want spirit box to work start to finish as a console based service: 

1. User opens SpiritBox exe or script (Windows/Mac/Linux) - console window pops up (cli agent starts) with a nice ASCII label on the top half showing SpiritBox label and realtime status notice, the bottom half will be the console where the user can start using SpiritBox. The top half console "banner" status will show real time notices like "Building spiritbox" and eventually "Ready for instruction" and then "Ready for extraction" when it's setup it ready to pull a file the user has defined. The console will have a clean, straight forward approach where the user can setup the following: 
    1. Activate SpiritBox ("Set-Conjure") by configuring/defining the file hash and file path that SpiritBox needs to watch out to extract immediately (no copies at all, moving from the endpoint to the container volume immediately). There can also be other parameters/flags like setting up multiple file paths or maybe using a different hash type (SHA256 vs SHA512).
    2. Once the correct parameters are set, the top banner of the Spirit Box console will show that it's configuring the "containment container" And would let the user know when it's ready the file to appear. Once that notice is received the user take the Necessary actions of bringing that particular file they need extracted to the endpoint. Box will monitor this file path in real time, spirit box will immediately extract this file once the hash matches, move it to a docker volume, Load the containment agent and docker container on load the necessary dependencies, load the heuristic agent monitoring agent logging agent and analysis agent and the docker container for the user their necessary analysis from Outside in.
    3. From here, the end user will be brought immediately to The analysis docker container that will be automatically Connected To the containment file via SSH and they can begin investigating the file in a secure, nested container environment. KEY POINTS: Capture container is completely isolated on its own volume and docker network, docker is set to READ ONLY on this container, no trust-based file validation, read-only filesystem, No external volumes, bind-mounts can be disabled entirely, Network stack is completely disabled, No interfaces, no DNS resolution, no sockets, Quantum-Safe Encryption (Optional), Image is minimal and immutable. 
2. Once the user is done with analyzing this file or files safely, the user will either close the window which they will be present with a gentle warning screen that the data extracted will be gone forever. Typing "exit" in the console will also show a similiar question. Once the user exits, Spirit box self destructs -completely- and leaves a single log file of everything (sbox.log).


2. Wegeb 

# AGENTS.md - SpiritBox™ Agent Manifest

This document outlines the ROUGH core agents and microservices that power **SpiritBox™** — the stateless containment utility by Exoterik Labs™. Each agent operates independently in stateless and ephemeral runtime containers (in memory), working under strict security constraints to ensure zero trust and zero persistence.

---

SpiritBox™ operates with two secure, ephemeral containers:

- **Capture Container**: Contains and isolates the threat quickly and immediately.
- **Analysis Container**: Provides a hardened forensic shell to investigate the captured file securely with monitoring, logging, and heuritic triggers in case the malware contained is attempting to escape.

Each agent listed below runs within or alongside these two containers. All agents operate with zero trust and assume no persistence.

---

## id: monitoring_agent
title: File Monitoring & Match Trigger
type: Passive (Host-Level)
description: >
  Monitors the configured watch path for new file events and matches against a specified SHA-256 hash. On a match, it spins up the capture container and passes the file.
responsibilities:
  - Watch target folder using inotify/FSEvents
  - Validate file hash against expected value
  - Trigger capture container on match
health_states:
  - healthy: Actively monitoring and responsive
  - degraded: Filewatch error or hash mismatch
  - fault: Unable to access watch path

---

## id: containment_agent
title: Capture & Isolation Agent
type: Ephemeral (Capture Container)
description: >
  Runs inside the capture container. Immediately moves the file into an isolated space (tmpfs or encrypted volume), applies strict read-only mount, and prepares for inspection.
responsibilities:
  - Lock and move file into capture container
  - Enforce strict read-only access
  - Apply encryption if configured
  - Signal analysis container to initialize
health_states:
  - healthy: File safely isolated
  - warning: Partial containment or encryption failed
  - fault: Capture container failed or corrupted

---

## id: analysis_agent
title: Analyst Shell & Static Analysis Tools
type: Interactive (Analysis Container)
description: >
  Operates within the hardened analyst container. Allows secure command-line access to review, scan, and analyze the isolated file using ClamAV, YARA, and entropy checks.
responsibilities:
  - Provide secure analyst terminal access
  - Run ClamAV, YARA, and heuristic scans
  - Enforce isolation from host
  - Generate scan report for export
health_states:
  - healthy: Shell accessible and tools functional
  - degraded: One or more analysis tools failed
  - fault: Container unreachable or compromised

---

## id: heuristic_agent
title: Runtime Behavior & Threat Monitoring
type: Behavioral (Inside Analysis Container)
description: >
  Monitors runtime behavior of tools and captured file in the analysis container. Terminates container if suspicious activity, privilege abuse, or sandbox escape is detected.
responsibilities:
  - Trace suspicious syscalls, memory use, process forks
  - Detect sandbox escape attempts
  - Log anomalies and flag for analyst review
  - Force shutdown on threat detection
health_states:
  - healthy: No anomalies detected
  - alert: Suspicious pattern detected
  - fault: Critical anomaly or breakout triggered shutdown

---

## id: logging_agent
title: Session Forensics Logger
type: Immutable (Analysis Container)
description: >
  Captures a tamper-proof forensic trail of the session: file hash, timestamps, scan results, agent events, and cleanup results. Log is encrypted and exported upon session end.
responsibilities:
  - Record all agent events and timestamps
  - Store logs temporarily in encrypted memory
  - Output final `.spiritlog.enc` file
  - Optional: sign with GPG or ARC key
health_states:
  - healthy: Logging successful
  - degraded: Log partially saved
  - fault: Log export or encryption failed

---

## id: cleanup_agent
title: Container Teardown & Ephemeral Self-Destruct
type: Auto (Analysis Container Final Task)
description: >
  Handles automated shutdown of both containers after analysis or anomaly detection. Securely wipes tmpfs storage and zeroes session keys. Leaves no trace behind.
responsibilities:
  - Stop containers and shred memory state
  - Wipe any temporary decrypted storage
  - Destroy session logs if flagged
  - Confirm zero-persistence before exit
health_states:
  - healthy: All artifacts wiped and containers destroyed
  - warning: Cleanup partial, retry triggered
  - fault: Shutdown or shred failure

---

## id: cli_agent
title: SpiritBox™ Console Shell
type: Interactive (Host-Level Interface)
description: >
  Provides a terminal interface for launching, configuring, and monitoring SpiritBox. User inputs are used to drive folder watching, hash validation, and analysis workflows.
responsibilities:
  - Display ASCII banner and menu
  - Accept user config for folder and hash
  - Launch containers and route input/output
  - Poll agent health and display log status
health_states:
  - healthy: Interface functional
  - degraded: Partial CLI failure or input error
  - fault: Menu crash or subprocess issue

---



---

## Runtime Container Overview

```plaintext
              [ Host System / Analyst Shell ]
                       │
       ┌───────────────┼────────────────┐
       ▼                               ▼

┌────────────────────┐        ┌────────────────────────┐
│  Capture Container  │        │   Analysis Container    │
│ (File Isolation)    │        │ (CLI + Scanners + Logs) │
└────────┬────────────┘        └────────────┬───────────┘
         │                                   │
         └── triggers ─────────────┬─────────┘
                                  ▼
                     Logs Encrypted + Containers Destroyed