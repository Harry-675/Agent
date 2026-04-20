from typing import List
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
import baostock as bs
import pandas as pd
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

def _now_cn() -> datetime:
    return datetime.now(ZoneInfo("Asia/Shanghai"))


def _build_system_prompt() -> str:
    now = _now_cn()
    return (
        "你是一个中文助手。需要实时信息时优先调用工具。"
        "你有四个工具：天气查询、网页搜索、股票查询、当前时间查询。"
        "股票代码示例：sh.600000、sh.600519、sz.000001。"
        f"当前系统时间（中国时区）是：{now.strftime('%Y-%m-%d %H:%M:%S')}。"
        "当用户询问天气/日期相关问题时，必须以此时间为基准，不要臆测今天日期。"
        "如果用户给了具体日期，请先判断该日期相对“当前系统时间”是过去、今天还是未来，再回答。"
        "回答中请简洁列出关键信息与时间。"
    )

USER_PROMPT_TEMPLATE = ChatPromptTemplate.from_template(
    "用户问题：{question}\n"
    "当前中国时间：{now_time}\n"
    "请优先判断是否需要调用工具（天气查询/网页搜索/股票查询/当前时间查询）。"
    "如果不需要工具，直接给出简洁准确的中文回答。"
)
STRING_PARSER = StrOutputParser()

WEATHER_CODE_MAP = {
    0: "晴",
    1: "大部晴朗",
    2: "局部多云",
    3: "阴",
    45: "有雾",
    48: "冻雾",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "大毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    80: "阵雨",
    81: "较强阵雨",
    82: "强阵雨",
    95: "雷阵雨",
}


@tool
def stock_history(
    code: str,
    start_date: str,
    end_date: str,
    frequency: str = "d",
    adjustflag: str = "3",
    csv_filename: str = "股票历史数据.csv",
) -> str:
    """查询A股历史行情并保存CSV。code示例 sh.600000 或 sz.000001。"""
    stock_code = (code or "").strip().lower()
    if not stock_code:
        return "股票代码为空，请提供 code，例如 sh.600000 或 sz.000001。"
    if not start_date or not end_date:
        return "请同时提供 start_date 和 end_date，格式例如 2024-01-01。"
    try:
        login_result = bs.login()
        if login_result.error_code != "0":
            return f"baostock 登录失败: {login_result.error_msg}"
        rs = bs.query_history_k_data_plus(
            code=stock_code,
            fields="date,open,high,low,close,volume,amount",
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjustflag=adjustflag,
        )
        if rs.error_code != "0":
            return f"历史行情查询失败: {rs.error_msg}"

        data_rows = []
        while rs.error_code == "0" and rs.next():
            data_rows.append(rs.get_row_data())
        df = pd.DataFrame(data_rows, columns=rs.fields)
        if df.empty:
            return f"未查询到 {stock_code} 在 {start_date}~{end_date} 的数据。"

        df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
        preview = df.head().to_string(index=False)
        return (
            f"股票历史数据（前5条）:\n{preview}\n\n"
            f"总条数: {len(df)}\n"
            f"已保存到: {csv_filename}"
        )
    except Exception as exc:
        return f"查询 {stock_code} 失败: {exc}"
    finally:
        try:
            bs.logout()
        except Exception:
            pass


@tool
def current_datetime(_: str = "") -> str:
    """查询当前中国时间。处理天气日期、今天/明天/后天等相对时间时请先调用。"""
    now = _now_cn()
    weekday_map = {
        0: "星期一",
        1: "星期二",
        2: "星期三",
        3: "星期四",
        4: "星期五",
        5: "星期六",
        6: "星期日",
    }
    return (
        f"当前中国时间: {now.strftime('%Y-%m-%d %H:%M:%S')} "
        f"{weekday_map[now.weekday()]}"
    )


def _normalize_date_text(date_text: str) -> str:
    now = _now_cn().date()
    raw = (date_text or "").strip()
    if not raw or raw in ("今天", "今日", "today"):
        return now.isoformat()
    if raw in ("明天", "tomorrow"):
        return (now + timedelta(days=1)).isoformat()
    if raw in ("后天",):
        return (now + timedelta(days=2)).isoformat()
    if raw in ("大后天",):
        return (now + timedelta(days=3)).isoformat()
    normalized = raw.replace("/", "-").replace(".", "-")
    try:
        if len(normalized) == 10:
            return datetime.strptime(normalized, "%Y-%m-%d").date().isoformat()
        if len(normalized) == 5:
            year = now.year
            return datetime.strptime(f"{year}-{normalized}", "%Y-%m-%d").date().isoformat()
    except ValueError:
        return ""
    return ""


@tool
def weather_forecast(city: str, date_text: str = "明天") -> str:
    """查询城市天气。date_text 支持 今天/明天/后天/YYYY-MM-DD/MM-DD。"""
    city_name = (city or "").strip()
    if not city_name:
        return "城市为空，请提供城市名，例如 北京、上海、杭州。"
    target_date = _normalize_date_text(date_text)
    if not target_date:
        return (
            "日期格式无法识别，请使用 今天/明天/后天 或 YYYY-MM-DD（例如 2026-04-21）。"
        )
    try:
        geo_resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city_name, "count": 1, "language": "zh", "format": "json"},
            timeout=12,
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        results = geo_data.get("results") or []
        if not results:
            return f"未找到城市 {city_name} 的地理信息，请尝试更完整的名称。"
        loc = results[0]
        lat = loc["latitude"]
        lon = loc["longitude"]
        resolved_city = loc.get("name", city_name)
        country = loc.get("country", "")

        weather_resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "Asia/Shanghai",
                "start_date": target_date,
                "end_date": target_date,
            },
            timeout=12,
        )
        weather_resp.raise_for_status()
        daily = weather_resp.json().get("daily") or {}
        dates = daily.get("time") or []
        if not dates:
            return f"{resolved_city} 在 {target_date} 暂无可用天气数据。"
        code = int((daily.get("weather_code") or [0])[0])
        max_temp = float((daily.get("temperature_2m_max") or [0])[0])
        min_temp = float((daily.get("temperature_2m_min") or [0])[0])
        rain_prob = int((daily.get("precipitation_probability_max") or [0])[0])
        weather_desc = WEATHER_CODE_MAP.get(code, f"天气代码 {code}")
        return (
            f"城市: {resolved_city} {country}\n"
            f"日期: {target_date}\n"
            f"天气: {weather_desc}\n"
            f"气温: {min_temp:.1f}~{max_temp:.1f}°C\n"
            f"降水概率: {rain_prob}%"
        )
    except Exception as exc:
        return f"查询天气失败: {exc}"


model = ChatOpenAI(
    model="MiniMax-M2.7",
    base_url="http://10.242.78.204:8080/v1",
    api_key="EMPTY",
    temperature=0,
)
web_search = DuckDuckGoSearchRun()
TOOLS = [weather_forecast, web_search, stock_history, current_datetime]
model_with_tools = model.bind_tools(TOOLS)
TOOLS_BY_NAME = {tool_obj.name: tool_obj for tool_obj in TOOLS}


def _call_tool(tool_name: str, args: object) -> str:
    tool_obj = TOOLS_BY_NAME.get(tool_name)
    if tool_obj is None:
        return f"未知工具: {tool_name}"
    try:
        if isinstance(args, dict):
            return str(tool_obj.invoke(args))
        return str(tool_obj.invoke({"query": str(args)}))
    except Exception as exc:
        return f"工具 {tool_name} 调用失败: {exc}"


def run_chat_round(
    history: List[BaseMessage], user_text: str, max_tool_rounds: int = 5
) -> str:
    """在已有会话历史上继续一轮对话，必要时自动调用工具。"""
    if not history or not isinstance(history[0], SystemMessage):
        history.insert(0, SystemMessage(content=_build_system_prompt()))
    prompt_msg = USER_PROMPT_TEMPLATE.format_messages(
        question=user_text, now_time=_now_cn().strftime("%Y-%m-%d %H:%M:%S")
    )[0]
    history.append(HumanMessage(content=prompt_msg.content))

    for _ in range(max_tool_rounds):
        ai_msg = model_with_tools.invoke(history)
        history.append(ai_msg)
        tool_calls = getattr(ai_msg, "tool_calls", None) or []
        if not tool_calls:
            return STRING_PARSER.invoke(ai_msg)
        for call in tool_calls:
            if isinstance(call, dict):
                name = call.get("name")
                args = call.get("args") or {}
                call_id = call.get("id") or ""
            else:
                name = getattr(call, "name", None)
                args = getattr(call, "args", None) or {}
                call_id = getattr(call, "id", None) or ""
            observation = _call_tool(str(name), args)
            history.append(ToolMessage(content=observation, tool_call_id=call_id))

    fallback = "工具调用轮次达到上限，请缩小问题范围后重试。"
    history.append(AIMessage(content=fallback))
    return fallback


if __name__ == "__main__":
    chat_history: List[BaseMessage] = []
    answer = run_chat_round(
        chat_history,
        "请查询 sh.600000 从 2024-01-01 到 2026-04-19 的历史行情，并简要说明北京今天天气。",
    )
    print(answer)
