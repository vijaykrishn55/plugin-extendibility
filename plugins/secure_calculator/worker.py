import ast
import json
import math
import operator
import sys


OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
       ast.Mod: operator.mod, ast.Pow: operator.pow}
UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
MAX_ABS = 1e12


def evaluate(node):
    if isinstance(node, ast.Expression):
        return evaluate(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        value = node.value
    elif isinstance(node, ast.BinOp) and type(node.op) in OPS:
        left, right = evaluate(node.left), evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 10:
            raise ValueError("Exponent magnitude must be at most 10")
        value = OPS[type(node.op)](left, right)
    elif isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
        value = UNARY[type(node.op)](evaluate(node.operand))
    else:
        raise ValueError("Only basic arithmetic expressions are allowed")
    if not math.isfinite(float(value)) or abs(value) > MAX_ABS:
        raise ValueError("Result exceeds allowed numeric range")
    return value


def handle(request):
    request_id = request.get("id", 1)
    try:
        expression = request["params"]["arguments"]["expression"]
        if not isinstance(expression, str) or len(expression) > 256:
            raise ValueError("Expression must be a string of at most 256 characters")
        tree = ast.parse(expression, mode="eval")
        result = evaluate(tree)
        return {"jsonrpc": "2.0", "id": request_id,
                "result": {"expression": expression, "value": result}}
    except Exception as exc:
        return {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32602, "message": str(exc)}}


def main():
    try:
        response = handle(json.loads(sys.stdin.readline()))
    except Exception as exc:
        response = {"jsonrpc": "2.0", "id": 1,
                    "error": {"code": -32600, "message": str(exc)}}
    print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
