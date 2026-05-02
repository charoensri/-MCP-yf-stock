import argparse
import traceback
from exceptiongroup import ExceptionGroup  # Python 3.11+

import asyncio
import json
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ollama import AsyncClient  # pip install ollama

load_dotenv()

def fetch_tool_identifier_prompt():
    tool_identifier_prompt = """
You have been given access to the below MCP Server Tools

{tools_description}

Identify the ONE appropriate tool from the above tools required to resolve the user query along with the arguments.

User Query:
{user_query}

Return ONLY JSON that matches this schema (no markdown, no extra text):
{{
  "user_query": "string",
  "tool_identified": "string",
  "arguments": {{ "key": "value" }}
}}

Rules:
- tool_identified must be exactly one of the tool names listed.
- arguments must match the tool input schema as best as possible.
- For tool "check_data_sources" (Yahoo Finance vs CSV health), use arguments: {{}} — no keys.
- For "get_stock_price" use arguments like {{ "symbol": "AAPL" }}.
- For "compare_stocks" use {{ "symbol1": "AAPL", "symbol2": "MSFT" }}.
"""
    return tool_identifier_prompt


class ToolSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_query: str
    tool_identified: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


async def generate_response(user_query: str, tools_description: str):
    """
    Use local Ollama to pick an MCP tool + arguments as JSON (schema-enforced).
    """
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1")
    
    print(f"ollama_host {ollama_host}")
    print(f"ollama_model {ollama_model}")

    client = AsyncClient(host=ollama_host)

    prompt = fetch_tool_identifier_prompt().format(
        user_query=user_query,
        tools_description=tools_description
    )

    # Enforce JSON schema output using Ollama structured outputs
    resp = await client.chat(
        model=ollama_model,
        messages=[
            {"role": "system", "content": "You are a strict JSON generator. Output must validate the provided schema."},
            {"role": "user", "content": prompt},
        ],
        format=ToolSelection.model_json_schema(),  # schema-constrained output
        options={"temperature": 0},
        stream=False,
    )

    print("=== OLLAMA RESPONSE ===")
    try:
        #print(json.dumps(resp, indent=2))
        print(resp)

    except* Exception as eg:
        print("[agent] ExceptionGroup caught")
        for e in eg.exceptions:
            traceback.print_exception(e)
        

    raw = (resp["message"]["content"] or "").strip()

    # Validate & parse according to schema
    try:
        data = ToolSelection.model_validate_json(raw).model_dump()
    except Exception:
        # Fallback: sometimes models still wrap content; try to recover
        raw2 = raw.replace("```json", "").replace("```", "").strip()
        data = ToolSelection.model_validate(json.loads(raw2)).model_dump()

    if data.get("tool_identified") == "check_data_sources":
        data["arguments"] = {}

    return data


async def main(user_input: str):
    print("-" * 50)
    print("The User Input is : ", user_input)

    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        cwd=r"C:\Users\chars1\OneDrive - Pegasystems Inc\0-29May25-NewLaptop\0-2025\0-AI\MCP-yf-stock\lab",
    )

    try:
        async with stdio_client(server_params) as (read, write):
            print("Connection established, creating session...")
            async with ClientSession(read, write) as session:
                print("[agent] Session created, initializing...")
                await session.initialize()
                print("[agent] MCP session initialized")

                tools = await session.list_tools()
                tools_description = ""
                for each_tool in tools.tools:
                    tools_description += f"Tool - {each_tool.name}:\n{each_tool.description}\n\n"

                print(f"------------------")
                print(f"tools_description {tools_description}\n")
                request_json = await generate_response(
                    user_query=user_input,
                    tools_description=tools_description
                )
                print(f"------------------")
                print(f"request_json {request_json}")
                print(
                    f"To execute the User Query: {user_input} - "
                    f"The Identified tool is {request_json['tool_identified']}, "
                    f"and the parameters required are {request_json['arguments']}"
                )

                response = await session.call_tool(
                    request_json["tool_identified"],
                    arguments=request_json["arguments"]
                )

                print(f"{response.content[0].text}")
                print("-" * 50)
                print("\n\n")

    except Exception as e:
        print(f"[agent] Error: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP stock client (Ollama tool routing)")
    parser.add_argument(
        "-q",
        "--query",
        metavar="TEXT",
        help="Run a single user query and exit (non-interactive)",
    )
    args = parser.parse_args()

    if args.query:
        asyncio.run(main(args.query))
    else:
        while True:
            query = input("What is your query? -> ")
            asyncio.run(main(query))