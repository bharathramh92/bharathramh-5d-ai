import re
from typing import Dict, Any, List, Tuple

class GuardrailsPolicyPlugin:
    """Output Guardrails and Safety Policy Plugin for agent outputs."""

    def __init__(self):
        self.disallowed_patterns = [
            (r'eval\(', "Disallowed dangerous dynamic eval execution"),
            (r'exec\(', "Disallowed dangerous dynamic exec execution"),
            (r'rm -rf /', "Disallowed dangerous root deletion command"),
            (r'DROP TABLE', "Disallowed destructive SQL drop table query")
        ]

    def validate_content(self, text: str) -> Tuple[bool, List[str]]:
        """Validates output text against safety policies and guardrails.

        Returns:
            Tuple[bool, List[str]]: (is_safe, list_of_violations)
        """
        violations = []
        if not isinstance(text, str):
            return True, []

        for pattern, reason in self.disallowed_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(reason)

        return len(violations) == 0, violations

    def sanitize_output(self, text: str) -> str:
        """Sanitizes disallowed patterns from LLM outputs."""
        if not isinstance(text, str):
            return text
        for pattern, reason in self.disallowed_patterns:
            text = re.sub(pattern, f"[SAFETY_BLOCKED: {reason}]", text, flags=re.IGNORECASE)
        return text

class HumanInTheLoopHook:
    """Human-in-the-loop (HITL) approval hook for high-consequence agent actions."""

    def __init__(self):
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}

    def request_approval(self, action_id: str, action_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        request_obj = {
            "action_id": action_id,
            "action_type": action_type,
            "details": details,
            "status": "PENDING_HUMAN_APPROVAL"
        }
        self.pending_approvals[action_id] = request_obj
        return request_obj

    def approve_action(self, action_id: str) -> bool:
        if action_id in self.pending_approvals:
            self.pending_approvals[action_id]["status"] = "APPROVED"
            return True
        return False

    def reject_action(self, action_id: str) -> bool:
        if action_id in self.pending_approvals:
            self.pending_approvals[action_id]["status"] = "REJECTED"
            return True
        return False
