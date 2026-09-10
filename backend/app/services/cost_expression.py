"""Evaluate the pricing expression grammar without executing user code."""
import ast
import math


def evaluate_expressions(expressions, terms, trip=None):
    trip = trip or {}
    scope = {t['key']: float(t.get('rate') or 0) for t in terms}
    scope.update(km=float(trip.get('km', 200)), kg=float(trip.get('tonnes', 15))*1000,
                 tonnes=float(trip.get('tonnes', 15)), stops=float(trip.get('stops', 1)),
                 legs=float(trip.get('legs', 1)), value=float(trip.get('value', 0)))
    values, visiting = {}, set()

    def calc(key):
        if key in values:
            return values[key]
        if key in visiting:
            raise ValueError('Công thức tham chiếu vòng tròn')
        visiting.add(key)
        source = str(expressions.get(key) or '').strip()
        if not source or len(source) > 2000:
            raise ValueError('Công thức trống hoặc quá dài')
        try:
            tree = ast.parse(source, mode='eval')
        except (SyntaxError, RecursionError) as exc:
            raise ValueError('Cú pháp công thức không hợp lệ') from exc
        if sum(1 for _ in ast.walk(tree)) > 512:
            raise ValueError('Công thức quá phức tạp')

        def visit(node):
            if isinstance(node, ast.Constant) and type(node.value) in (int, float):
                value = float(node.value)
            elif isinstance(node, ast.Name):
                if node.id in ('COST', 'REV', 'PROFIT'):
                    value = calc(node.id)
                elif node.id in scope:
                    value = scope[node.id]
                else:
                    raise ValueError('Không nhận ra biến: ' + node.id)
            elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                value = visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
            elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                a, b = visit(node.left), visit(node.right)
                if isinstance(node.op, ast.Div) and b == 0:
                    raise ValueError('Không thể chia cho 0')
                value = a+b if isinstance(node.op, ast.Add) else a-b if isinstance(node.op, ast.Sub) else a*b if isinstance(node.op, ast.Mult) else a/b
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                  and node.func.id in ('min', 'max', 'abs') and not node.keywords
                  and 0 < len(node.args) <= 20):
                args = [visit(a) for a in node.args]
                if node.func.id == 'abs':
                    if len(args) != 1:
                        raise ValueError('abs cần một tham số')
                    value = abs(args[0])
                else:
                    value = (min if node.func.id == 'min' else max)(args)
            else:
                raise ValueError('Phép toán không được hỗ trợ')
            if not math.isfinite(value) or abs(value) > 1e18:
                raise ValueError('Kết quả vượt giới hạn')
            return value

        values[key] = visit(tree.body)
        visiting.remove(key)
        return values[key]

    cost, revenue, profit = calc('COST'), calc('REV'), calc('PROFIT')
    return dict(cost=cost, revenue=revenue, profit=profit, perKm=cost/scope['km'] if scope['km'] > 0 else 0,
                marginPct=profit/revenue*100 if revenue else None)
