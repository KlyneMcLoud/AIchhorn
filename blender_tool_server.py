# blender_tool_server.py
from mcp import MCPServer, tool
import subprocess

server = MCPServer(name="blender-runner", version="0.1")

@tool(name="run_blender_code", description="Führt Python-Code in Blender aus.")
def run_blender_code(code: str) -> str:
    try:
        subprocess.run(["blender", "--background", "--python-expr", code], check=True)
        return "✅ Code erfolgreich ausgeführt"
    except subprocess.CalledProcessError as e:
        return f"❌ Fehler: {e}"

server.start()