# SpiritBox™
<img width="615" height="410" alt="image" src="https://github.com/user-attachments/assets/43167bf4-dd13-4388-83e5-c0db5334c28d" />

<img width="639" height="166" alt="image" src="https://github.com/user-attachments/assets/cb7c5b44-dea5-454b-96e5-4d77cb047dc6" />

SpiritBox™ is a stateless, transient, secure extraction and containment service for isolating malware or other files directly on endpoints in real time. Designed for ultra-fast containment and absolute zero-trust file handling, SpiritBox monitors for specified file hashes (and/or a folder path) and instantly extracts that suspicious file (or files) into a nested container. From there, professionals can safely inspect the file in a hardened shell environment with minimal to no risk of compromise. SpiritBox is also auto-ephemral by design. Once analysis is completed, SpiritBox auto-deletes itself (containers, files, scripts, exes, everything) and leaves only a single log file ("sbox-log.txt"), leaving little traces of it ever existing.

---

## ⚙️ Key Features & Design Philosophy

- 🧿 **Targeted Real-Time Detection**
  - Watches for file appearances in predefined folders.
  - Matches using SHA-256 hash, filename, or other identifiers.

- 🕳 **Instant Virtualization & Containment**
  - Securely locks the file inside a temporary, ephemeral container.
  - File is inaccessible to the endpoint from the moment it is caught.

- 🔐 **Quantum-Safe Encryption**
  - All inter-container communications use PQC-compatible encryption.
  - Optional: Preshared post-quantum key exchange on boot.

- 🧼 **Stateless & Ephemeral by Default**
  - Containers self-destruct after execution.
  - Nothing persists unless explicitly saved by the user.

- 🪬 **Two-Layer Container Architecture**
  - **Inner Container**: Captures and contains the malicious file.
  - **Outer Container**: Shell-accessible forensic environment with built-in tools (YARA, ClamAV, custom heuristics).

- 🧠 **Heuristic Analysis Agent**
  - Monitors for anomalous behaviors from the contained file.
  - Auto-triggers shutdown if tampering or escapes are attempted.

- 🧾 **Audit & Log Report**
  - Generates a local, encrypted `.log` file summarizing the session.
  - Can be moved back to the endpoint for secure archiving.

- 🎛 **No External Calls**
  - Entirely offline-first and air-gapped compatible.
  - Built for analysts, red teamers, and SOC responders.

---

## 🕷 Exoterik Labs™ Mission

> *Security software for people.*  
> Exoterik Labs™ builds privacy-centric, hardened security tools designed to protect individuals and organizations from the evolving threat landscape. We believe security should be transparent, open-source, and aggressively aligned with user privacy. SpiritBox™ is part of our effort to bring elite-grade digital containment into the hands of real users — no enterprise bloat, no telemetry, no compromise.

---

## 🚀 Getting Started

### 🔧 Requirements

- Docker or Podman installed (Linux preferred)
- Python 3.11+ (optional for custom CLI)
- 2+ vCPU / 2GB RAM minimum
- No internet required after initial setup

---

### 📦 Installation

```bash
git clone https://github.com/exoteriklabs/SpiritBox.git
cd SpiritBox
./install.sh

## Prototype CLI

The current repository provides a Python-based prototype of the SpiritBox console.
It models the agent manifest from `AGENTS.md` and wires each agent into an orchestrated
workflow that can be exercised from a terminal session.

### Running the CLI

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
spiritbox --banner cli/assets/banner.txt  # Optional custom banner path
```

Within the console you can:

- `set_conjure <folder> <sha256>` — configure the watch path and expected hash.
- `activate` — start monitoring for the target file.
- `status` — inspect agent health, the most recent analysis report, and heuristic alerts.
- `export` — write the session log (`sbox-log.txt`) to the SpiritBox workspace.
- `self_destruct` — tear down the workspace and exit.

### Agent Wiring

- **Monitoring Agent** polls the configured folder and triggers on the matching SHA-256.
- **Containment Agent** stages the captured file inside an isolated workspace folder.
- **Analysis Agent** performs lightweight static checks (hash, entropy, mock AV/YARA).
- **Heuristic Agent** raises alerts for suspicious findings (e.g., high entropy).
- **Logging Agent** records every event and exports `sbox-log.txt`.
- **Cleanup Agent** erases the workspace to honor the zero-persistence requirement.

This implementation focuses on the control plane and in-memory orchestration described
in the agent manifest. Containerization, virtualization, and advanced tooling can be layered
on top of this foundation in subsequent iterations.
