#!/usr/bin/env python3
import sys
import json
import urllib.request
import urllib.error

def main():
    # Read from stdin line by line
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            # Parse the JSON-RPC request
            req = json.loads(line)
            
            # Forward JSON-RPC request to the local FastAPI server
            req_data = json.dumps(req).encode('utf-8')
            http_req = urllib.request.Request(
                "http://localhost:8000/mcp",
                data=req_data,
                headers={'Content-Type': 'application/json'}
            )
            
            try:
                # Send request and read response
                with urllib.request.urlopen(http_req) as response:
                    res_data = response.read().decode('utf-8')
                    
                    # In JSON-RPC, notifications (requests without an 'id') should not receive a response.
                    # We forward it to the server but do not print the response back to stdio.
                    if "id" in req:
                        sys.stdout.write(res_data + "\n")
                        sys.stdout.flush()
            
            except urllib.error.URLError as e:
                # Handle connection errors (e.g. server not running)
                if "id" in req:
                    err = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603, 
                            "message": f"HTTP request failed: {e}. Is the Nash Arena backend server running at http://localhost:8000?"
                        },
                        "id": req.get("id")
                    }
                    sys.stdout.write(json.dumps(err) + "\n")
                    sys.stdout.flush()
                
        except json.JSONDecodeError:
            # Handle invalid JSON input
            err = {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            }
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()
            
        except Exception as e:
            # Handle other unexpected errors
            req_id = req.get("id", None) if 'req' in locals() and isinstance(req, dict) else None
            if req_id is not None:
                err = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": str(e)},
                    "id": req_id
                }
                sys.stdout.write(json.dumps(err) + "\n")
                sys.stdout.flush()

if __name__ == "__main__":
    main()
