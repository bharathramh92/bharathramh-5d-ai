import sys
from pathlib import Path

# Add root directory to sys.path
root_dir = str(Path(__file__).resolve().parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.agent import MultiAgentCodeArchSystem

class Agent:
    """Standard Agent interface wrapper for benchmark evaluators."""

    def __init__(self, api_key: str = None, session_id: str = "default"):
        self.system = MultiAgentCodeArchSystem(api_key=api_key, session_id=session_id)

    def run(self, prompt: str = "") -> str:
        if not prompt or prompt.strip().startswith("/") or "analyze" in prompt.lower():
            report = self.system.run_full_analysis(".")
            return report.get("documentation", {}).get("system_spec", str(report))
        return self.system.answer_architecture_question(prompt)

    def invoke(self, input_data: dict) -> dict:
        target_dir = input_data.get("target_dir", ".") if isinstance(input_data, dict) else "."
        return self.system.run_full_analysis(target_dir)

def run_agent(prompt: str = "") -> str:
    agent = Agent()
    return agent.run(prompt)

# Re-export MultiAgentCodeArchSystem
__all__ = ["Agent", "MultiAgentCodeArchSystem", "run_agent"]

if __name__ == "__main__":
    import sys
    prompt = sys.argv[1] if len(sys.argv) > 1 else ""
    print(run_agent(prompt))
