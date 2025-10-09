from crewai.tools import BaseTool
import ast
import operator
import re

# 计算器工具，方便进行预算开销的计算
class CalculatorTool(BaseTool):
  name: str = "计算器工具"
  description: str = (
      "用于执行加减乘除等数学计算。"
      "输入应为表达式，例如 200*7 或 5000/2*10。"
  )

  def _run(self, operation: str):
    try:
      allowed_operators = {
          ast.Add: operator.add,
          ast.Sub: operator.sub,
          ast.Mult: operator.mul,
          ast.Div: operator.truediv,
          ast.Pow: operator.pow,
          ast.Mod: operator.mod,
          ast.USub: operator.neg,
          ast.UAdd: operator.pos,
      }

      if not re.match(r'^[0-9+\-*/().% ]+$', operation):
        raise ValueError("数学表达式包含无效字符")

      tree = ast.parse(operation, mode='eval')

      def _eval_node(node):
        if isinstance(node, ast.Expression):
          return _eval_node(node.body)
        elif isinstance(node, ast.Constant):
          return node.value
        elif isinstance(node, ast.Num):
          return node.n
        elif isinstance(node, ast.BinOp):
          left = _eval_node(node.left)
          right = _eval_node(node.right)
          op = allowed_operators.get(type(node.op))
          if op is None:
            raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
          return op(left, right)
        elif isinstance(node, ast.UnaryOp):
          operand = _eval_node(node.operand)
          op = allowed_operators.get(type(node.op))
          if op is None:
            raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
          return op(operand)
        else:
          raise ValueError(f"不支持的语法节点: {type(node).__name__}")

      return _eval_node(tree)

    except (SyntaxError, ValueError, ZeroDivisionError, TypeError) as e:
      raise ValueError(f"计算错误: {str(e)}")
    except Exception:
      raise ValueError("无效的数学表达式")
