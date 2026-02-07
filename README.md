# custom-spaces-python-api

## Product Description

The Custom Spaces Python API adds an agentic layer on top of the Custom Spaces tool backend API in order to facilitate agentic interaction. It uses the assistant-gateway for this purpose, enabling AI agents to interact with the Custom Spaces backend through a conversational interface.

## Getting Started

### Prerequisites

The assistant-gateway needs to be installed locally into the environment using the `-e` flag:

```bash
pip install -e /path/to/assistant-gateway
```

For example:
```bash
pip install -e /home/mihir/projects/assistant-gateway
```

### Environment Variables

Set the following environment variables in your `.env` file:

- `ANTHROPIC_API_KEY` - Your Anthropic API key (if using Claude)
- `CLAUDE_MODEL` - Default Claude model to use (e.g., `claude-3-5-sonnet-20241022`)
- `BACKEND_URL` - URL for the Custom Spaces backend API (e.g., `http://localhost:5000`, `http://172.23.176.1:5000`)

### Starting the API

To start the FastAPI instance:

```bash
python -m space_assistant_gateway.app
```

or 

```bash
fastapi dev app.py --port 8000
```

### Windows/WSL Networking Note

If the backend API is running on Windows localhost but the Space Gateway API is running on WSL, you'll need to map the localhost address:

- Windows: `http://localhost:5000`
- WSL (for agent tool calls): `http://172.23.176.1:5000`

Replace `172.23.176.1` with your actual WSL host IP if different. You can find it by running `ip route show | grep -i default | awk '{ print $3}'` in WSL.
