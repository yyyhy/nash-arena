import sys
import json
import asyncio

# 导入你封装好的网关类
from src.mcp_gateway.server import MCPGateway

async def run_stdio():
    # 1. 实例化你的网关
    gateway = MCPGateway()
    
    # 获取当前的事件循环，用于异步读取控制台输入
    loop = asyncio.get_running_loop()
    
    # 2. 开启一个无限循环，持续监听 Glama 机器人发来的标准输入 (stdio)
    while True:
        # 异步读取一行输入
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break  # 如果读不到数据 (EOF)，说明机器人断开了连接，安全退出
            
        line = line.strip()
        if not line:
            continue
            
        try:
            # 解析 Glama 发来的 JSON-RPC 请求
            request_dict = json.loads(line)
            
            # 3. 灵魂调用：直接把你写好的核心处理方法借过来用！
            # 注意：你的 _handle_jsonrpc 返回的是 FastAPI 的 JSONResponse 对象
            response_obj = await gateway._handle_jsonrpc(request_dict)
            
            # 4. 从 FastAPI 的 JSONResponse 中提取出原始 bytes 字节流，转为字符串
            response_str = response_obj.body.decode('utf-8')
            
            # 5. 把处理结果输出到标准输出 (stdout)，机器人就能看到了
            sys.stdout.write(response_str + "\n")
            sys.stdout.flush()  # 必须 flush，确保数据瞬间发出去
            
        except json.JSONDecodeError:
            # 捕获 JSON 解析错误
            error_resp = json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            })
            sys.stdout.write(error_resp + "\n")
            sys.stdout.flush()
        except Exception as e:
            # 捕获其他运行时报错，保证服务器不崩溃
            error_resp = json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": None
            })
            sys.stdout.write(error_resp + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    # 防止 Python 缓冲导致输出不及时，这是过 Glama 审查的绝对核心
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    # 启动 stdio 监听模式
    asyncio.run(run_stdio())
