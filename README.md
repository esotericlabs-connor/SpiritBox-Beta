# SpiritBox™
<img width="615" height="410" alt="image" src="https://github.com/user-attachments/assets/43167bf4-dd13-4388-83e5-c0db5334c28d" />

<img width="639" height="166" alt="image" src="https://github.com/user-attachments/assets/cb7c5b44-dea5-454b-96e5-4d77cb047dc6" />

SpiritBox™ is a stateless, secure containment system for isolating malware/files locally on endpoints in real time, safely. Designed for ultra-fast response and zero-trust file handling, SpiritBox monitors for specified file events and instantly transfers suspicious files into an ephemeral, encrypted container. From there, analysts can safely inspect the file in a hardened shell environment without risk of compromise. The system is self-destructing, stateless, and hardened against both traditional and quantum threats.

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
