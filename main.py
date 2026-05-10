import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
load_dotenv(PROJECT_ROOT / ".env")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from my_project.chain import ask_agent


def main():
    parser = argparse.ArgumentParser(description="LangChain 파이프라인 추천 에이전트")
    parser.add_argument("--query", required=True, help="추천받고 싶은 앱 아이디어를 입력하세요")
    args = parser.parse_args()
    result = ask_agent(args.query)
    print(result["answer"])


if __name__ == "__main__":
    main()
