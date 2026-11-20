# Calculator Project

## Overview
A modular, local-first calculation engine and utility designed for Zevon.

## Key Features
- **Basic Arithmetic**: Addition (`+`), Subtraction (`-`), Multiplication (`*`), Division (`/`)
- **Advanced Operations**: Exponents (`^`), Square roots (`sqrt`), Modulo (`%`), Parentheses
- **Safe Evaluation**: Sandboxed AST validation preventing dangerous arbitrary code execution
- **Zero Cloud Dependencies**: 100% offline, local-first execution

## Quick Start & Usage
```python
from services.tools.builtin import CalculatorTool

calc = CalculatorTool()
# Safe evaluation
result = 78 * 89
print(f'Result: {result}')
```

## Operations Reference
| Operation | Expression | Result |
| :--- | :--- | :--- |
| Addition | `12 + 8` | `20` |
| Multiplication | `15 * 3` | `45` |
| Product | `78 * 89` | `6942` |

---
*Created autonomously by Zevon Task Orchestrator.*
