# MuesliSwap SAM
## Sockets Across Machines

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/release/MuesliSwapLabs/muesliswap-sockets-across-machines.svg)](https://github.com/MuesliSwapLabs/muesliswap-sockets-across-machines/releases)

## Overview

*MuesliSwap Sockets Across Machines* is a tool designed to facilitate seamless communication between local applications and a remote Cardano node. By creating a local socket that proxies requests to the remote node, users can interact with the Node as if it were running locally.

This tool has undergone thorough fine-tuning and optimization, making it ready for testing in limited production environments.

## Features

- **Seamless Integration**: Interact with a remote Cardano node using local applications without modifying existing workflows.
- **User-Friendly Setup**: Simplified installation and configuration process with minimal user intervention.
- **Secure**: All transmission happen via encrypted connections, and no ports are opened to the public.
- **Transparency and Open Source**: Fully transparent operations with the source code available for community review and contributions.

## Table of Contents

- [Background](#background)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
  - [Server Setup](#server-setup)
  - [Client Setup](#client-setup)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Future Development](#future-development)
- [License](#license)

## Background

In distributed environments, accessing a remote Cardano node via its socket securely and efficiently can be challenging. This tool addresses that by allowing local applications to communicate with a remote node via a local socket, streamlining development and operational processes.

## Getting Started

### Prerequisites

- **Just**: Command run helper, which is used to setup and start the server.
- **Python 3.6+**: Ensure Python is installed on both the client and server machines.
- **SSH Access**: SSH key-based authentication set up between the client and server.
- **Sudo Access**: Ensure that there is passwordless sudo access on server.
- **Cardano Node**: A running Cardano node on the server machine.
- **Operating System**: Compatible with Unix-like systems (Linux, macOS).

### Installation

Clone the repository to both your client and server machines:

```bash
git clone https://github.com/MuesliSwapLabs/muesliswap-sockets-across-machines.git
```

Navigate to the project directory:

```bash
cd muesliswap-sockets-across-machines
```

Prepare the local environment:

```bash
just setup
```

## Usage

On the **client machine** where you want to access the Cardano node:

1. **Start the Client Script**:
   This will create a 

   ```bash
   just run user@your.server.ip:/path/to/node/socket/file ./node.socket
   ```

   - Replace `your.server.ip` with the server's IP address or hostname.
   - Replace `user` with the user for which SSH access and passwordless sudo has been setup
   - Replace `/path/to/node/socket/file` with the remote path to the Cardano Node Socket file
   - Replace `./node.socket` with the path where you want the socket file to be created

2. **Set Environment Variable**:

   - Export the `CARDANO_NODE_SOCKET_PATH` environment variable to point to the local socket:

     ```bash
     export CARDANO_NODE_SOCKET_PATH=./node.socket
     ```

3. **Interact with Cardano CLI**:

   - You can now use `cardano-cli` commands as if the node were running locally.

### Example

A video demonstration showcasing the setup and usage is available on [YouTube](https://www.youtube.com/watch?v=R2UPOUbuo5U) and as a 
[direct download](https://github.com/MuesliSwapLabs/muesliswap-sockets-across-machines/blob/main/reports/2/example_usage.avi).

## Troubleshooting

- **Connection Refused**:

  - Verify that the server script is running and accessible.
  - Check firewall settings on both client and server machines.

- **Permission Denied**:

  - Ensure you have read/write permissions for the socket paths on both the server and client.

- **Cardano CLI Errors**:

  - Confirm that `CARDANO_NODE_SOCKET_PATH` is correctly set on the client.
  - Check that the Cardano node is fully synchronized on the server.

## Contributing

We welcome contributions from the community! To contribute:

1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Submit a pull request with a detailed description of your changes.

Your feedback is valuable. Please [open an issue](https://github.com/MuesliSwapLabs/muesliswap-sockets-across-machines/issues) to suggest enhancements or report bugs.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Additional Documentation

For more detailed information on the underlying processes of this tool, refer to the [project report](reports/1/report.pdf), which includes technical specifications, design decisions, and optimization strategies undertaken during development.

## Transparency and Open Source

The entire codebase is open-source and available for review. We believe in transparency and encourage community involvement to improve and evolve the project.
