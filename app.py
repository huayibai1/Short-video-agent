from __future__ import annotations

from pathlib import Path

import streamlit as st

from modules.config_store import (
    apply_provider_profile,
    embedding_model_config,
    load_config,
    save_config,
    text_model_kwargs,
)
from modules.pipeline import create_project, generate_preview_plan
from modules.vector_store import VectorStore


def render_table(rows: list[dict], columns: list[tuple[str, str]]) -> None:
    if not rows:
        st.write("暂无数据。")
        return
    header = "".join(f"<th>{label}</th>" for _, label in columns)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{str(row.get(key, ''))}</td>" for key, _ in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    st.markdown(
        f"""
        <div class="table-wrap">
          <table class="agent-table">
            <thead><tr>{header}</tr></thead>
            <tbody>{''.join(body_rows)}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="AI短视频生成 Agent", page_icon="🎬", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --paper: #f7f3ea;
        --porcelain: #fffdfa;
        --linen: #eee6d8;
        --ink: #24231f;
        --graphite: #67645d;
        --olive: #53624b;
        --moss: #dce4d2;
        --clay: #b7815d;
        --line: rgba(36, 35, 31, 0.12);
        --shadow: 0 18px 45px rgba(36, 35, 31, 0.08);
    }
    .stApp {
        background:
            radial-gradient(circle at 18% 0%, rgba(220, 228, 210, 0.55) 0, transparent 29rem),
            radial-gradient(circle at 92% 12%, rgba(183, 129, 93, 0.16) 0, transparent 24rem),
            var(--paper);
        color: var(--ink);
    }
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        background-image:
            linear-gradient(rgba(36, 35, 31, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(36, 35, 31, 0.05) 1px, transparent 1px);
        background-size: 36px 36px;
        mask-image: linear-gradient(to bottom, black, transparent 82%);
        z-index: 0;
    }
    .block-container {
        position: relative;
        z-index: 1;
        padding-top: 1.1rem;
        max-width: 1240px;
    }
    h1, h2, h3, p, label, span, div {
        letter-spacing: 0 !important;
    }
    h1, h2, h3, p, label, span, div,
    .stMarkdown, .stText, .stCaption, .stDataFrame,
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] *,
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] *,
    [data-baseweb="tab"],
    [data-baseweb="tab"] *,
    .stButton button,
    .stButton button *,
    .stDownloadButton button,
    .stDownloadButton button *,
    .stAlert,
    .stAlert * {
        color: var(--ink) !important;
    }
    h1, h2, h3 {
        font-family: Cambria, Georgia, serif !important;
        font-weight: 900 !important;
    }
    [data-testid="stSidebar"] {
        background: rgba(238, 230, 216, 0.94);
        border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] * {
        color: var(--ink) !important;
    }
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
        background: var(--porcelain) !important;
        color: var(--ink) !important;
        border: 1px solid rgba(36, 35, 31, 0.16) !important;
        border-radius: 9px !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid var(--line);
    }
    .stTabs [data-baseweb="tab"] {
        background: var(--porcelain);
        color: var(--ink) !important;
        border: 1px solid var(--line);
        border-radius: 12px 12px 0 0;
        padding: 11px 18px;
        box-shadow: inset 0 0 0 1px rgba(36, 35, 31, 0.05);
    }
    .stButton button, .stDownloadButton button {
        background: var(--moss) !important;
        color: var(--ink) !important;
        border: 1px solid rgba(36, 35, 31, 0.18) !important;
        border-radius: 9px !important;
        font-weight: 700 !important;
    }
    .hero {
        position: relative;
        display: grid;
        grid-template-columns: minmax(0, 1fr) 390px;
        gap: 24px;
        align-items: stretch;
        margin-bottom: 22px;
        border-bottom: 1px solid var(--line);
        padding: 18px 0 24px;
    }
    .hero-main {
        background: transparent;
        color: var(--ink);
        padding: 8px 0;
    }
    .hero-main h1 {
        color: var(--ink) !important;
        margin: 8px 0 16px 0;
        font-size: clamp(44px, 6vw, 78px);
        line-height: 0.96;
        max-width: 850px;
    }
    .hero-main p {
        color: var(--graphite) !important;
        margin: 0;
        font-size: 17px;
        line-height: 1.8;
        max-width: 760px;
    }
    .hero-side {
        background: var(--porcelain);
        border: 1px solid var(--line);
        padding: 20px;
        box-shadow: var(--shadow), inset 0 0 0 1px rgba(36, 35, 31, 0.06);
    }
    .hero-side b {
        display: block;
        color: var(--olive);
        margin-bottom: 10px;
        font-family: "Cascadia Mono", Consolas, monospace;
        font-size: 12px;
        text-transform: uppercase;
    }
    .hero-side p {
        color: var(--ink) !important;
        margin: 0;
    }
    .metric-strip {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin: 16px 0 22px 0;
    }
    .metric-strip div {
        background: var(--porcelain);
        border: 1px solid var(--line);
        box-shadow: inset 0 0 0 1px rgba(36, 35, 31, 0.06);
        padding: 12px;
        min-height: 82px;
    }
    .metric-strip b {
        display: block;
        font-size: 13px;
        color: var(--graphite);
        margin-bottom: 6px;
    }
    .metric-strip span {
        color: var(--ink);
        font-size: 18px;
        font-weight: 800;
        line-height: 1.25;
    }
    .note-box {
        background: var(--porcelain);
        border-left: 7px solid var(--clay);
        border-top: 1px solid var(--line);
        border-right: 1px solid var(--line);
        border-bottom: 1px solid var(--line);
        padding: 12px 14px;
        color: var(--ink);
        box-shadow: inset 0 0 0 1px rgba(36, 35, 31, 0.05);
    }
    .eyebrow {
        color: var(--olive);
        font-family: "Cascadia Mono", Consolas, monospace;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0 !important;
    }
    .model-roadmap {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 12px;
        margin: 14px 0 20px;
    }
    .model-roadmap div {
        background: var(--porcelain);
        border: 1px solid var(--line);
        padding: 14px;
        min-height: 126px;
        box-shadow: inset 0 0 0 1px rgba(36, 35, 31, 0.05);
    }
    .model-roadmap b {
        display: block;
        color: var(--ink);
        margin: 6px 0;
    }
    .model-roadmap span {
        color: var(--olive);
        font-family: "Cascadia Mono", Consolas, monospace;
        font-size: 10px;
        text-transform: uppercase;
    }
    .model-roadmap p {
        color: var(--graphite) !important;
        font-size: 13px;
        line-height: 1.55;
        margin: 0;
    }
    .table-wrap {
        overflow-x: auto;
        border: 1px solid var(--line);
        background: var(--porcelain);
        margin-bottom: 14px;
    }
    .agent-table {
        width: 100%;
        border-collapse: collapse;
        color: var(--ink);
        font-size: 14px;
    }
    .agent-table th {
        background: var(--linen);
        color: var(--ink) !important;
        text-align: left;
        padding: 10px;
        white-space: nowrap;
        border-bottom: 1px solid var(--line);
    }
    .agent-table td {
        border-top: 1px solid var(--line);
        color: var(--ink);
        padding: 10px;
        vertical-align: top;
        min-width: 96px;
    }
    @media (max-width: 900px) {
        .hero, .metric-strip, .model-roadmap {
            grid-template-columns: 1fr;
        }
    }
    </style>
    <div class="hero">
      <div class="hero-main">
        <div class="eyebrow">short video agent / mcp ready workflow</div>
        <h1>把短视频任务拆成可调度的 Agent 流程。</h1>
        <p>用户只输入一句主题，LLM 生成图像提示词、视频提示词和配音文案；生图模型生成参考图，I2V 视频模型基于参考图生成片段，TTS 配音，最后合成 MP4。</p>
      </div>
      <div class="hero-side">
        <b>required model map</b>
        <p>框架：LangGraph 编排 Agent 节点。主链路：LLM -> 生图 -> I2V 视频 -> TTS -> 合成。RAG 仅作展示。</p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


config = load_config()

with st.sidebar:
    st.header("快速控制")
    use_llm = st.toggle("调用文本大模型", value=bool(config["text_model"]["enabled"]))
    use_rag = st.toggle("启用 RAG 检索", value=True)
    generate_now = st.button("生成短视频", type="primary", use_container_width=True)
    st.markdown(
        """
        <div class="note-box">
        答辩演示建议：先在“模型配置”保存 API，再到“创作输入”填写标题和提示词，最后生成 MP4。
        </div>
        """,
        unsafe_allow_html=True,
    )


tab_input, tab_config, tab_knowledge, tab_preview = st.tabs(["一句话生成", "模型配置", "知识库", "预览导出"])

with tab_input:
    st.subheader("只输入一句话主题")
    topic = st.text_area("一句话主题", "AI如何帮助大学生高效学习", height=120)
    title = ""
    audience = "短视频观众"
    style = "真实竖屏短视频，画面自然，节奏清晰，适合中文平台"
    duration_seconds = 60
    scene_count = 15
    custom_prompt = (
        "你将根据用户的一句话主题，自动生成一个 60 秒中文竖屏短视频方案。"
        "必须生成 15 个分镜，每个分镜都要有 narration、subtitle、image_prompt、video_prompt。"
        "image_prompt 用于生图模型生成 I2V 参考图，必须是中文详细画面描述，真实摄影风格，无文字、无水印、无 logo。"
        "video_prompt 用于视频模型基于参考图生成动态片段，必须描述镜头运动、人物动作和氛围，无字幕、无水印、无乱码文字。"
        "voiceover 要适合 TTS 配音，中文口语化，整体时长约 60 秒。"
    )
    st.markdown(
        """
        <div class="note-box">
        固定生成参数：60 秒、15 个分镜。标题、受众、风格、配音文案、图像提示词、视频提示词全部由 LLM 自动生成。
        </div>
        """,
        unsafe_allow_html=True,
    )

with tab_config:
    st.markdown(
        """
        <div class="eyebrow">model access map</div>
        <div class="model-roadmap">
          <div><span>required</span><b>文本大模型</b><p>生成标题、脚本、分镜、字幕文案，是 Agent 的主推理模型。</p></div>
          <div><span>recommended</span><b>Embedding / RAG</b><p>把资料变成检索上下文，当前可用本地 TF-IDF，后续可接 Embedding API。</p></div>
          <div><span>required</span><b>图像生成模型</b><p>根据 image_prompt 生成 I2V 参考图，是画面贴合分镜的关键。</p></div>
          <div><span>required</span><b>视频生成模型</b><p>基于参考图和 video_prompt 生成动态片段。</p></div>
          <div><span>required</span><b>本地合成工具</b><p>统一控制字幕、配音、时长并导出 MP4。</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    model_tabs = st.tabs(["文本大模型", "Embedding/RAG", "图像生成", "TTS 语音", "视频生成", "本地合成工具"])
    config_keys = ["text_model", "embedding_model", "image_model", "tts_model", "video_model", "render_engine"]
    tab_labels = ["文本大模型", "Embedding/RAG", "图像生成", "TTS 语音", "视频生成", "本地合成工具"]
    with st.expander("硅基流动统一配置", expanded=True):
        profile = config["provider_profile"]
        p1, p2 = st.columns(2)
        with p1:
            profile["provider"] = st.text_input("供应商", profile.get("provider", "SiliconFlow"), key="profile_provider")
            profile["base_url"] = st.text_input("统一 Base URL", profile.get("base_url", "https://api.siliconflow.cn/v1"), key="profile_base_url")
        with p2:
            profile["api_key"] = st.text_input("统一 API Key", profile.get("api_key", ""), type="password", key="profile_api_key")
            profile["usage"] = st.text_area("说明", profile.get("usage", ""), key="profile_usage", height=80)
        if st.button("同步到所有 API 模型", use_container_width=True):
            config = apply_provider_profile(config)
            save_config(config)
            st.success("已同步供应商、Base URL 和 API Key 到文本、Embedding、TTS、视频生成模型。")
    for model_tab, config_key, label in zip(model_tabs, config_keys, tab_labels):
        with model_tab:
            current = config[config_key]
            if config_key == "text_model":
                st.markdown('<div class="note-box">必须配置。接入 Claude Code 后，MCP 工具内部会调用这里的文本模型生成脚本和分镜。</div>', unsafe_allow_html=True)
            elif config_key == "embedding_model":
                st.markdown('<div class="note-box">推荐配置。当前本地 TF-IDF 已可演示 RAG，若老师强调向量检索，可升级为 Embedding API。</div>', unsafe_allow_html=True)
            elif config_key == "tts_model":
                st.markdown('<div class="note-box">必须保留。视频生成模型通常不能稳定替代配音，TTS 更适合生成可控旁白。</div>', unsafe_allow_html=True)
            elif config_key == "image_model":
                st.markdown('<div class="note-box">必须配置。I2V 视频模型需要参考图，生图模型负责根据分镜 image_prompt 生成参考图。</div>', unsafe_allow_html=True)
            elif config_key == "video_model":
                st.markdown('<div class="note-box">必须配置。这里使用 I2V 视频模型，基于参考图和 video_prompt 生成视频片段。</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="note-box">必须保留。最终 MP4 的时长、字幕、音频混合和导出由本地合成工具控制。</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                current["enabled"] = st.checkbox(f"启用{label}", value=bool(current.get("enabled")), key=f"{config_key}_enabled")
                current["provider"] = st.text_input("Provider", current.get("provider", ""), key=f"{config_key}_provider")
                current["model"] = st.text_input("模型名", current.get("model", ""), key=f"{config_key}_model")
            with c2:
                current["base_url"] = st.text_input("Base URL", current.get("base_url", ""), key=f"{config_key}_base_url")
                if config_key in {"text_model", "embedding_model", "image_model", "tts_model", "video_model"}:
                    current["endpoint"] = st.text_input("Endpoint", current.get("endpoint", ""), key=f"{config_key}_endpoint")
                if config_key == "image_model":
                    current["image_size"] = st.text_input("Image Size", current.get("image_size", "720x1280"), key=f"{config_key}_image_size")
                    current["batch_size"] = st.number_input("Batch Size", min_value=1, max_value=4, value=int(current.get("batch_size", 1) or 1), key=f"{config_key}_batch_size")
                if config_key == "video_model":
                    current["status_endpoint"] = st.text_input("Status Endpoint", current.get("status_endpoint", ""), key=f"{config_key}_status_endpoint")
                    current["max_scene_videos"] = st.number_input("生成前 N 个分镜视频", min_value=0, max_value=15, value=int(current.get("max_scene_videos", 15) or 15), key=f"{config_key}_max_scene_videos")
                    current["poll_interval"] = st.number_input("轮询间隔秒", min_value=5, max_value=60, value=int(current.get("poll_interval", 12) or 12), key=f"{config_key}_poll_interval")
                    current["max_wait_seconds"] = st.number_input("最大等待秒", min_value=60, max_value=1800, value=int(current.get("max_wait_seconds", 600) or 600), key=f"{config_key}_max_wait_seconds")
                if config_key == "tts_model":
                    current["voice"] = st.text_input("Voice", current.get("voice", ""), key=f"{config_key}_voice")
                if config_key == "text_model":
                    current["timeout"] = st.number_input("Timeout 秒", min_value=30, max_value=600, value=int(current.get("timeout", 180) or 180), key=f"{config_key}_timeout")
                if config_key == "embedding_model":
                    current["encoding_format"] = st.text_input("Encoding Format", current.get("encoding_format", "float"), key=f"{config_key}_encoding_format")
                    current["batch_size"] = st.number_input("Batch Size", min_value=1, max_value=128, value=int(current.get("batch_size", 16) or 16), key=f"{config_key}_batch_size")
                current["api_key"] = st.text_input("API Key", current.get("api_key", ""), type="password", key=f"{config_key}_api_key")
                current["usage"] = st.text_area("用途说明", current.get("usage", ""), key=f"{config_key}_usage", height=88)
    if st.button("保存模型配置", use_container_width=True):
        path = save_config(config)
        st.success(f"模型配置已保存到本机数据库：{path}")

with tab_knowledge:
    st.subheader("RAG 知识库")
    store = VectorStore()
    st.write(f"当前知识库文本块数量：`{len(store.documents)}`")
    embedded_count = sum(1 for doc in store.documents if doc.get("embedding"))
    st.write(f"已向量化文本块：`{embedded_count}`")
    st.caption("启用 Embedding/RAG 并配置硅基流动 Key 后，上传资料会自动写入语义向量。旧资料可点击下方按钮重建。")
    uploaded = st.file_uploader("上传 TXT/MD 资料", type=["txt", "md"])
    if uploaded is not None:
        text = uploaded.getvalue().decode("utf-8", errors="ignore")
        count = VectorStore().add_text(text, uploaded.name, embedding_model_config(config))
        st.success(f"已写入知识库：{count} 个文本块")
    if st.button("使用 Embedding API 重建向量索引", use_container_width=True):
        result = VectorStore().rebuild_embeddings(embedding_model_config(config))
        if result["ok"]:
            st.success(f"{result['message']} 已更新 {result['updated']}/{result['total']} 个文本块，模型：{result.get('model', '')}")
        else:
            st.error(result["message"])
    query = st.text_input("检索测试", topic if "topic" in locals() else "")
    if st.button("检索知识库"):
        render_table(
            VectorStore().search(query, 5, embedding_model_config(config)),
            [("score", "相关度"), ("retrieval", "检索方式"), ("source", "来源"), ("text", "内容")],
        )

model_kwargs = text_model_kwargs(config)
embedding_kwargs = embedding_model_config(config)
if "llm_preview_requested" not in st.session_state:
    st.session_state.llm_preview_requested = False
with tab_preview:
    col_preview_action, col_preview_note = st.columns([0.24, 0.76])
    with col_preview_action:
        if st.button("刷新 LLM 预览", use_container_width=True):
            st.session_state.llm_preview_requested = True
    with col_preview_note:
        st.caption("为避免推理模型频繁超时，页面默认使用本地快速预览；点击按钮后才调用文本大模型刷新预览。最终生成仍会按侧边栏开关调用模型。")

preview_plan = generate_preview_plan(
    topic=topic,
    title=title,
    custom_prompt=custom_prompt,
    audience=audience,
    style=style,
    duration_seconds=duration_seconds,
    scene_count=scene_count,
    use_llm=use_llm and st.session_state.llm_preview_requested,
    use_rag=use_rag,
    embedding_config=embedding_kwargs,
    **model_kwargs,
)

with tab_preview:
    st.markdown(
        f"""
        <div class="metric-strip">
          <div><b>标题</b><span>{preview_plan['title']}</span></div>
          <div><b>时长</b><span>{preview_plan['duration_seconds']} 秒</span></div>
          <div><b>分镜</b><span>{preview_plan['scene_count']} 个</span></div>
          <div><b>生成模式</b><span>{preview_plan.get('generation_mode', 'unknown')}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if preview_plan.get("llm_error"):
        st.warning(f"模型调用失败，已降级模板生成：{preview_plan['llm_error']}")
    st.subheader("视频概述")
    st.write(preview_plan["summary"])
    st.subheader("配音文案")
    st.text_area("Voiceover", preview_plan["voiceover"], height=220, label_visibility="collapsed")
    st.subheader("分镜表")
    render_table(
        [
            {
                "镜头": scene["index"],
                "时间": f"{scene['start']:.2f}-{scene['end']:.2f}s",
                "画面": scene["visual"],
                "字幕": scene["subtitle"],
                "素材关键词": scene["asset_keyword"],
            }
            for scene in preview_plan["scenes"]
        ],
        [("镜头", "镜头"), ("时间", "时间"), ("画面", "画面"), ("字幕", "字幕"), ("素材关键词", "素材关键词")],
    )
    st.subheader("RAG 检索来源")
    if preview_plan.get("rag_sources"):
        render_table(
            preview_plan["rag_sources"],
            [("score", "相关度"), ("retrieval", "检索方式"), ("source", "来源"), ("text", "内容")],
        )
    else:
        st.write("暂无检索结果。")

if generate_now:
    with st.spinner("正在生成脚本、字幕、配音、画面和 MP4..."):
        result = create_project(
            topic=topic,
            title=title,
            custom_prompt=custom_prompt,
            audience=audience,
            style=style,
            duration_seconds=duration_seconds,
            scene_count=scene_count,
            use_llm=use_llm,
            use_rag=use_rag,
            embedding_config=embedding_kwargs,
            **model_kwargs,
        )
    st.success("生成完成")
    st.write(f"输出目录：`{result['project_dir']}`")
    st.write(f"生成模式：`{result['generation_mode']}`，RAG 命中：`{result['rag_hit_count']}`")
    st.write(f"Agent 框架：`{result.get('agent_framework', 'pipeline')}`")
    if result.get("graph_steps"):
        st.write("LangGraph 节点：`" + " -> ".join(result["graph_steps"]) + "`")
    if not result["audio_muxed"]:
        st.warning("当前环境没有可用 ffmpeg，已生成静音 MP4 和单独 WAV 配音。安装 imageio-ffmpeg 后可自动合成音频。")
    files = result["files"]
    video_path = Path(files["final_video"])
    st.video(str(video_path))
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("下载 MP4", video_path.read_bytes(), file_name="final_video.mp4")
    with col2:
        st.download_button("下载字幕 SRT", Path(files["subtitles"]).read_bytes(), file_name="subtitles.srt")
    with col3:
        st.download_button("下载方案 Markdown", Path(files["markdown"]).read_bytes(), file_name="video_plan.md")
