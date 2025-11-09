Please follow according to this manifest: 

SpiritBox™ is a stateless, transient, and ephemeral file/malware extraction, containment and detonation service for isolating malware or other files directly on endpoints in real time. Designed for ultra-fast containment and absolute zero-trust file handling, SpiritBox monitors for specified file hashes (and/or a folder path) and instantly extracts that suspicious file (or files) into a nested container. From there, professionals can safely inspect the file in a hardened shell environment with minimal to no risk of compromise. SpiritBox is also auto-ephemral by design. Once analysis is completed, SpiritBox auto-deletes itself (containers, files, scripts, exes, everything) and leaves only a single log file ("sbox-log.txt"), leaving little traces of it ever existing.

As infrastructure, Spirit box runs entirely in memory under THREE nested docker containers: The inner container (container 1) called "extraction and detonation container", the middle container (container 2) called "bridge and analysis container" and the outer counter (container 3) we just call “cli and configuration container”. 

Container 1 runs almost entirely in C++ as it’s main goal is to confirm, extract and container the targeted file at ultra-fast speeds. Once container 1 has finished configuration, it sends the call to container 2 to build itself agreeing on the port number for SSH during that time.

Container 2 kicks in once container 1 confirms completion, container 2 is built as a nested container -inside- of container 1 and handles analysis, heuristics, forensic tools controlled by container 3 and bridging SSH between container 1 and container 3. Container 2 also has the responsibility to self-destruct container 1 in case it begins to try to begin lateral movement. 

Container 3 is the cli and configuration container. This container has two lives: the initial setup when you target a file path and hash and then after when containers 1 and 2 are built. This ensures that the 3 containers are nested properly. This container is responsible for the user CLI, requesting file path and hash for extraction, and then providing the user with the 2nd CLI interface after the file extraction and environment (container 1 and 2 are complete) 

We want all dependencies/libraries of the detonation container to be loaded and ready before Spirit Box is "ready to extract" the targeted file. All containers are on their own network and only communicate through a pre-agreed port for SSH at random (NOT 22). 

Here is how we want spirit box to work start to finish as a console based service from the user experience: 

1. User opens SpiritBox exe or script (Windows/Mac/Linux) - console window pops up (cli agent/CONTAINTER 3 starts) with a nice ASCII label on the top half showing SpiritBox label and realtime status notice, the bottom half will be the console where the user can start using SpiritBox. The top half console "banner" status will show real time notices like "Building spiritbox" and eventually "Ready for instruction" and then "Ready for extraction" when it's setup it ready to pull a file the user has defined. The console will have a clean, straight forward approach where the user can setup the following: 
    1. Activate SpiritBox ("Set-Conjure") by configuring/defining the file hash and file path that SpiritBox needs to watch out to extract immediately (no copies at all, moving from the endpoint to the container volume immediately, all in memory under restriced resources using C++ code). There can also be other parameters/flags like setting up multiple file paths or maybe using a different hash type (SHA256 vs SHA512).
    2. Once the correct parameters are set, the top banner of the Spirit Box console will show that it's configuring the "containment" And would let the user know when it's ready the file to appear. Once that notice is received, the user can take the necessary actions of bringing that particular file they need extracted to the endpoint. SpiritBox will monitor this file path in real time, spirit box will immediately extract this file once the hash matches, move it to a restricted memory space immediately using C++ code, build it into container 1 on it's own volume and network with no internet. Once containter 1 is built, it will give the signal to container 2 to build itself around container 1 to begin heuristic analysis and SSH bridge. After that, container 3 is  
    3. From here, the end user will be brought immediately to a new SSH session (container 3 recreated in the same window) that will be automatically xonnected To the containment file via SSH bridge through container 2 and they can begin investigating the file in a secure, nested container environment. KEY POINTS: ALL CONTAINERS are completely isolated on its own volume and docker network, docker is set to READ ONLY on these containers, no trust-based file validation, read-only filesystem after configuration, No external volumes, bind-mounts can be disabled entirely, Network stack is completely disabled except for whats required for SSH, No interfaces, no DNS resolution, no sockets, Quantum-Safe SHA-512 Encryption, Image is minimal and immutable. 
2. Once the user is done with analyzing this file or files safely, the user will either close the window which they will be present with a gentle warning screen that the data extracted will be gone forever. Typing "exit" in the console will also show a similiar question. Once the user exits, Spirit box intiates the logging agent to send a global organized log to the clean_up agent. Once received, SpiritBox self destructs -completely- and leaves a the single log file of everything (sbox.log) provided by the cleanup_agent just before it closes. Everything from SpritBox runs entirely in memory. 


2. Wegeb 

# AGENTS.md - SpiritBox™ Agent Manifest

This document outlines the core agents and microservices that power **SpiritBox™** — the stateless containment utility by Exoterik Labs™. Each agent operates independently in stateless and ephemeral runtime containers (in memory), working under strict security constraints to ensure zero trust and zero persistence.

---

SpiritBox™ operates with three docker containers:

- **Inner: Extraction and Detonation Container**
  - Built under C++ for speed and hardware-level control
  - File extraction/containment only
  - Container quickly/efficiently matches file with hash under the file path configured, moves  

- **Middle: Analysis and Bridge Container**
  - Built entirely around container 1 once call is received. 
  - Accesses container 1 via SSH (Random, predetermined port for SSH only) and builds a bridge to allow connection for CLI (container 3)
  - Forensic tools, logging, heuristic monitoring provided for container 3 to apply to container 1. 

- **Outer: Console and Configuration Container**
  - CLI interface
  - Handles user interface, configuration and realtime monitoring 
  - Launches lifecycle and handles orchestration
  - When file hash matches and containment is made, this container is immeditately rebuit to complete nesting of containers 1 , 2, and 3 with 1 being the core. 
  - Triggers self-destruct sequence once user exits from SpiritBox, removing everything and only leaving a log file

Each agent listed below runs within these three containers. All agents operate with zero trust and assume no persistence. All agents run in memory. 

---
## id: cli_agent
title: SpiritBox™ Console Shell
type: Interactive (Container 3)
description: >
  Main user interface shown on launch. Displays ASCII header, container statuses, real-time agent updates, and allows the user to configure hash/path detection. Provides a terminal interface for launching, configuring, and monitoring SpiritBox. User inputs are used to drive folder watching, hash validation, and analysis workflows.
responsibilities:
  - Display ASCII banner and menu
  - Show system status and ready state
  - Accept user config for folder and hash
  - Launch containers and route input/output
  - Poll agent health and display log status
  - Handle exit prompt and self-destruct call
health_states:
  - healthy: Interface functional
  - degraded: Partial CLI failure or input error
  - fault: Menu crash or subprocess issue

---
## id: containment_agent
title: Initial Monitoring, Capture & Isolation Agent
type: Ephemeral (Container 1)
description: >
  Runs inside the capture container. Immediately moves the file into an isolated space (tmpfs or encrypted volume), applies strict read-only mount, and prepares for inspection.
responsibilities:
  - Identify file per file path/hash
  - Lock and move file into capture container
  - Enforce strict read-only access after creation
  - Apply enforced SHA-512 AES encryption 
  - Wait for SSH request from analysis container
  - Signal analysis container to initialize
health_states:
  - healthy: File safely isolated
  - warning: Partial containment or encryption failed
  - fault: Capture container failed or corrupted

---
## id: bridge_agent
title: Container 1 to container 2 SSH bridge
type: Passive (container 2)
description: >
  Used to build the SSH bridge between container 1 and 3 using a random predetermined port number.
responsibilities:
  - Watch target folder using inotify/FSEvents
  - Validate file hash against expected value
  - Trigger capture container on match
health_states:
  - healthy: Actively monitoring and responsive
  - degraded: Filewatch error or hash mismatch
  - fault: Unable to access watch path

---

## id: analysis_agent
title: Analyst Shell & Static Analysis Tools
type: Interactive (Container 2)
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
type: Behavioral (Container 2)
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
type: Immutable (Container 2)
description: >
  Captures a tamper-proof forensic trail of the session: file hash, timestamps, scan results, agent events, and cleanup results. Log is encrypted and exported upon session end.
responsibilities:
  - Record all agent events and timestamps
  - Store logs temporarily in encrypted memory
  - Output final `.spiritlog.log` file
  - Optional: sign with GPG or ARC key
health_states:
  - healthy: Logging successful
  - degraded: Log partially saved
  - fault: Log export or encryption failed

---

## id: cleanup_agent
title: Container Teardown & Ephemeral Self-Destruct
type: Auto (Container 2 and 3)
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

## Container Flow Overview (3-Layer Stack)

```plaintext
            ┌────────────────────────────────────────┐
            │          OUTER CONTAINER               │
            │    (cli_agent + cleanup_agent)         │
            └──────────────┬─────────────────────────┘
                           │ SSH (Dynamic port mapping for SSH only)
            ┌──────────────▼────────────────────────┐
            │         MIDDLE CONTAINER              │
            │ (analysis_agent + heuristic_agent     │
            │  + logging_agent + bridge_agent)      |
            └──────────────┬────────────────────────┘
                           │   SSH (Dynamic port mapping for SSH only)
            ┌──────────────▼────────────────────────┐
            │           INNER CONTAINER             │
            │   (detonation + containment_agent)    |
            └───────────────────────────────────────┘

            **all containers are on their own network and volume. 
            **all infrastructure