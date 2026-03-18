import uvicorn
from src.mcp_gateway.server import MCPGateway


def main():
    gateway = MCPGateway()
    uvicorn.run(gateway.app, host="0.0.0.0", port=8008)


if __name__ == "__main__":
    main()
