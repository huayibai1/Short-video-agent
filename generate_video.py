from __future__ import annotations

import argparse
import json

from modules.pipeline import create_project


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a 1-minute short video package.")
    parser.add_argument("--topic", default="请输入你要生成的视频主题", help="视频主题")
    parser.add_argument("--title", default="", help="用户指定视频标题")
    parser.add_argument("--prompt", default="", help="用户自定义生成提示词")
    parser.add_argument("--audience", default="大学生", help="目标受众")
    parser.add_argument("--style", default="科技感", help="视频风格")
    parser.add_argument("--duration", type=int, default=60, help="视频时长，单位秒")
    parser.add_argument("--scenes", type=int, default=16, help="分镜数量，15-20")
    parser.add_argument("--use-llm", action="store_true", help="调用 OpenAI 兼容模型生成脚本")
    parser.add_argument("--no-rag", action="store_true", help="关闭 RAG 知识库检索")
    parser.add_argument("--api-key", default=None, help="OpenAI 兼容 API Key，也可用 OPENAI_API_KEY")
    parser.add_argument("--base-url", default=None, help="OpenAI 兼容 Base URL，也可用 OPENAI_BASE_URL")
    parser.add_argument("--model", default=None, help="模型名，也可用 OPENAI_MODEL")
    args = parser.parse_args()

    result = create_project(
        args.topic,
        title=args.title,
        custom_prompt=args.prompt,
        audience=args.audience,
        style=args.style,
        duration_seconds=args.duration,
        scene_count=args.scenes,
        use_llm=args.use_llm,
        use_rag=not args.no_rag,
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
