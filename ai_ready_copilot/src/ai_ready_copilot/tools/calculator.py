import math

ALLOWED_MATH = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "pi": math.pi,
    "e": math.e,
}

def calculator(expression: str) -> dict:
    """
    Evalúa una expresión matemática simple con python.

    Args:
        expression (str): La expresión de python a evaluar.

    Returns:
        dict: status y resultado o mensaje de error.
    """
    try:
        result = eval(expression, {"__builtins__": {}, **ALLOWED_MATH})
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
    