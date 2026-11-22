"""CLI-запуск агента.

Использование:
    python main.py "создай задачу 'купить хлеб'"
"""

import sys

from agent import build_agent


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print('Использование: python main.py "<запрос на естественном языке>"', file=sys.stderr)
        return 2

    query = sys.argv[1]
    agent = build_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": query}]})
    answer = result["messages"][-1].content
    print(answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
