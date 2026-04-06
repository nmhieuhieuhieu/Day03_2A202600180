import os
import re
from typing import List, Dict, Any, Optional, Callable
from dotenv import load_dotenv
from src.core.llm_provider import LLMProvider
from src.core.openai_provider import OpenAIProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
from src.tools.tools import TOOLS, execute_tool


class ReActAgent:
    """
    ReAct Agent v1: Thought -> Action -> Observation loop.
    """

    def __init__(
        self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 7
    ):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []
        self.tool_executor: Optional[Callable] = None  # set externally from tools.py

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join(
            [f"- {t['name']}: {t['description']}" for t in self.tools]
        )
        return f"""You are TravelWise, an expert Vietnamese travel assistant.
                You help users plan trips with real-time data by using tools.

                Available tools:
                {tool_descriptions}

                You MUST follow this exact format for every step:

                Thought: <your reasoning about what to do next>
                Action: tool_name[argument]
                Observation: <you will see the tool result here>

                You can repeat Thought/Action/Observation multiple times.
                When you have enough information, respond with:

                Thought: I now have all the information needed.
                Final Answer: <your complete answer in Vietnamese, formatted in Markdown>

                IMPORTANT RULES:
                - Always start with a Thought before any Action.
                - Use EXACTLY the format Action: tool_name[argument] with square brackets.
                - Do NOT make up information. Only use data from tool observations.
                - If a search returns no useful result, try a different query.
                - Answer in Vietnamese.
                """

    def run(self, user_input: str) -> str:
        logger.log_event(
            "AGENT_START", {"input": user_input, "model": self.llm.model_name}
        )

        # Build the initial prompt with conversation history
        prompt_parts = [f"User question: {user_input}\n"]
        steps = 0
        final_answer = None

        while steps < self.max_steps:
            current_prompt = "".join(prompt_parts)

            # Generate LLM response
            result = self.llm.generate(
                current_prompt, system_prompt=self.get_system_prompt()
            )
            content = result["content"]

            # Track metrics
            tracker.track_request(
                provider=result.get("provider", "unknown"),
                model=self.llm.model_name,
                usage=result.get("usage", {}),
                latency_ms=result.get("latency_ms", 0),
            )

            latency = result.get("latency_ms", 0)
            print(f"\n{'─'*50}")
            print(f"  STEP {steps + 1}  ({latency}ms)")
            print(f"{'─'*50}")

            logger.log_event(
                "AGENT_STEP",
                {
                    "step": steps + 1,
                    "raw_output": content[:500],  # truncate for log
                    "latency_ms": result.get("latency_ms", 0),
                },
            )
            logger.log_event("AGENT_STEP", {
                "step": steps + 1,
                "raw_output": content[:500],  # truncate for log
                "latency_ms": latency,
            })

            # Check for Final Answer
            final_match = re.search(r"Final Answer:\s*(.*)", content, re.DOTALL)
            if final_match:
                final_answer = final_match.group(1).strip()
                prompt_parts.append(content)
                # Print thought before final answer if present
                thought_match = re.search(r"Thought:\s*(.*?)(?=Final Answer:)", content, re.DOTALL)
                if thought_match:
                    print(f"  Thought: {thought_match.group(1).strip()}")
                print(f"  >> Final Answer found")
                break

            # Parse Action: tool_name[argument]
            action_match = re.search(r"Action:\s*(\w+)\[([^\]]*)\]", content)
            if action_match:
                tool_name = action_match.group(1)
                tool_args = action_match.group(2)

                # Print thought if present
                thought_match = re.search(r"Thought:\s*(.*?)(?=Action:)", content, re.DOTALL)
                if thought_match:
                    print(f"  Thought: {thought_match.group(1).strip()}")

                print(f"\n  >> Calling tool: {tool_name}")
                print(f"     Args: {tool_args}")

                logger.log_event("TOOL_CALL", {"tool": tool_name, "args": tool_args})

                # Execute tool
                observation = self._execute_tool(tool_name, tool_args)

                print(f"\n  << Tool result ({tool_name}):")
                for line in observation.splitlines():
                    print(f"     {line}")

                logger.log_event("TOOL_RESULT", {
                    "tool": tool_name,
                    "result": observation[:300],  # truncate for log
                })

                # Append everything up to Action, then add Observation
                # Only keep up to the Action line from LLM output
                action_end = content[: action_match.end()]
                prompt_parts.append(action_end + f"\nObservation: {observation}\n\n")
            else:
                # No Action and no Final Answer — LLM might be confused
                print(f"  !! Parse error: No Action or Final Answer found")
                print(f"     Output preview: {content[:200]}")
                logger.log_event("PARSE_ERROR", {
                    "step": steps + 1,
                    "reason": "No Action or Final Answer found",
                    "output": content[:300],
                })
                # Nudge the agent to follow the format
                prompt_parts.append(
                    content
                    + "\n\nYou must either use Action: tool_name[argument] or provide Final Answer:.\n\n"
                )

            steps += 1

        # If we exhausted max_steps without Final Answer
        if final_answer is None:
            logger.log_event("AGENT_TIMEOUT", {"steps": steps})
            final_answer = "Xin lỗi, tôi không thể hoàn thành yêu cầu trong số bước cho phép. Vui lòng thử lại với câu hỏi cụ thể hơn."

        logger.log_event(
            "AGENT_END", {"steps": steps, "has_answer": final_answer is not None}
        )

        self.history.append(
            {"input": user_input, "output": final_answer, "steps": steps}
        )
        return final_answer

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """Execute a tool using the external tool_executor function."""
        if self.tool_executor:
            return self.tool_executor(tool_name, args)
        return f"Error: No tool executor configured. Cannot run '{tool_name}'."


def main():
    load_dotenv()

    model_name = os.getenv("DEFAULT_MODEL", "gpt-4o")
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set. Please configure it in your environment or .env file.")

    react_agent = ReActAgent(
        llm=OpenAIProvider(model_name=model_name, api_key=api_key),
        tools=TOOLS,
    )

    react_agent.run(
        "Tôi muốn đi du lịch Đà Nẵng vào cuối tuần này. Hãy giúp tôi lên kế hoạch chi tiết, bao gồm dự báo thời tiết, gợi ý khách sạn, và những địa điểm ăn uống nổi tiếng. Tôi cũng muốn biết tổng chi phí ước tính cho chuyến đi này."
    )


main()
