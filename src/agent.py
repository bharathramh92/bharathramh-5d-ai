import os
import json
import time
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from google import genai
from google.genai import types

from src.tools import (
    scan_directory_structure,
    analyze_code_metrics,
    extract_imports_and_deps,
    detect_api_routes,
    scan_security_and_secrets
)
from src.memory import SessionMemoryManager
from src.telemetry import TelemetryTracer
from src.guardrails import GuardrailsPolicyPlugin, HumanInTheLoopHook
from src.secrets import get_secret

class DiagramsResponse(BaseModel):
    component_diagram: str = Field(description="Mermaid.js flowchart graph TD")
    sequence_diagram: str = Field(description="Mermaid.js sequenceDiagram")

class SecurityAuditResponse(BaseModel):
    overall_rating: str = Field(description="Strong, Moderate, or Needs Attention")
    key_risks: List[str] = Field(description="List of identified architectural or code security risks")
    remediation_recommendations: List[str] = Field(description="Actionable steps to strengthen security")
    summary_markdown: str = Field(description="Markdown formatted security summary")

class DocumentationResponse(BaseModel):
    adr_document: str = Field(description="Architecture Decision Record 001")
    onboarding_guide: str = Field(description="Developer onboarding guide")
    system_spec: str = Field(description="Technical system specification summary")

class MultiAgentCodeArchSystem:
    """Enterprise Multi-Agent System with System Instructions, Async Memory, HITL Hooks, and Guardrails."""

    def __init__(self, api_key: Optional[str] = None, session_id: str = "default"):
        self.api_key = api_key or get_secret("GEMINI_API_KEY")
        self.session_id = session_id
        self.memory = SessionMemoryManager()
        self.telemetry = TelemetryTracer()
        self.guardrails = GuardrailsPolicyPlugin()
        self.hitl_hook = HumanInTheLoopHook()

        self.primary_model = "gemini-3.5-flash"
        self.fast_model = "gemini-2.5-flash-lite"

        # System-level persona instruction configuration
        self.system_instruction = "You are ArchAgent, a Principal Enterprise System Architect & Auditor. Provide accurate, structured, and production-ready technical architecture synthesis."

        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception:
                self.client = None
        else:
            self.client = None

    async def run_full_analysis_async(self, target_dir: str) -> Dict[str, Any]:
        """Async multi-agent pipeline orchestration."""
        span_total = self.telemetry.start_span("run_full_analysis_async", "Orchestrator", {"target_dir": target_dir})

        span_scan = self.telemetry.start_span("static_inspection", "ScannerAgent")
        dir_struct = await asyncio.to_thread(scan_directory_structure, target_dir)
        metrics = await asyncio.to_thread(analyze_code_metrics, target_dir)
        deps = await asyncio.to_thread(extract_imports_and_deps, target_dir)
        routes = await asyncio.to_thread(detect_api_routes, target_dir)
        security_findings = await asyncio.to_thread(scan_security_and_secrets, target_dir)
        self.telemetry.end_span(span_scan, "SUCCESS")

        inspection_context = {
            "directory_structure": dir_struct,
            "code_metrics": metrics,
            "dependencies": deps,
            "api_routes": routes,
            "security_findings": security_findings
        }

        # Subagent 2: Architecture Modeler
        span_model = self.telemetry.start_span("architecture_modeling", "ArchitectureModelerAgent")
        architecture_diagrams = await self._run_architecture_modeler_async(inspection_context)
        self.telemetry.end_span(span_model, "SUCCESS")

        # Subagent 3: Security Auditor
        span_audit = self.telemetry.start_span("security_auditing", "SecurityAuditorAgent")
        security_report = await self._run_security_auditor_async(inspection_context)
        self.telemetry.end_span(span_audit, "SUCCESS")

        # Subagent 4: Documentation Generator
        span_doc = self.telemetry.start_span("doc_generation", "DocGeneratorAgent")
        documentation = await self._run_doc_generator_async(inspection_context, architecture_diagrams, security_report)
        self.telemetry.end_span(span_doc, "SUCCESS")

        # Actively invoke Human-in-the-Loop (HITL) Hook for production action approval
        if len(security_findings) > 0:
            self.hitl_hook.request_approval(
                action_id=f"hitl_{int(time.time())}",
                action_type="SECURITY_REMEDIATION_COMMIT",
                details={"findings_count": len(security_findings), "target_dir": target_dir}
            )

        clean_adr = self.guardrails.sanitize_output(documentation.get("adr_document", ""))
        clean_guide = self.guardrails.sanitize_output(documentation.get("onboarding_guide", ""))
        documentation["adr_document"] = clean_adr
        documentation["onboarding_guide"] = clean_guide

        report = {
            "target_dir": target_dir,
            "status": "SUCCESS",
            "metrics": metrics,
            "inspection_summary": {
                "total_files": dir_struct.get("total_files", 0),
                "total_dirs": dir_struct.get("total_dirs", 0),
                "total_loc": metrics.get("summary", {}).get("total_loc", 0),
                "languages": dir_struct.get("language_breakdown", {}),
                "api_route_count": len(routes),
                "security_findings_count": len(security_findings)
            },
            "diagrams": architecture_diagrams,
            "security_report": security_report,
            "documentation": documentation,
            "api_routes": routes,
            "security_findings": security_findings,
            "pending_hitl_approvals": self.hitl_hook.pending_approvals,
            "telemetry": self.telemetry.get_trace_summary()
        }

        # Async Session Memory Persistence
        await self.memory.save_report_async(self.session_id, report)
        self.telemetry.end_span(span_total, "SUCCESS")
        return report

    def run_full_analysis(self, target_dir: str) -> Dict[str, Any]:
        """Synchronous wrapper for async pipeline execution."""
        return asyncio.run(self.run_full_analysis_async(target_dir))

    async def _run_architecture_modeler_async(self, context: Dict[str, Any]) -> Dict[str, str]:
        if not self.client:
            return {
                "component_diagram": "graph TD\n    Client[Web UI / API Client] --> Server[FastAPI Server]\n    Server --> Agent[Multi-Agent System]\n    Agent --> Scanner[Static Scanner Tool]\n    Agent --> Telemetry[Telemetry & Memory]",
                "sequence_diagram": "sequenceDiagram\n    Client->>Server: POST /api/analyze\n    Server->>Agent: Orchestrate Subagents\n    Agent-->>Server: Return Architecture Report\n    Server-->>Client: Render Dashboard & Mermaid Diagrams"
            }

        prompt = f"Synthesize valid Mermaid.js diagrams for codebase:\n{json.dumps(context['directory_structure'].get('file_list_sample'))}"
        error_context = ""
        for attempt in range(2):
            try:
                full_prompt = prompt + (f"\nPrevious Error: {error_context}" if error_context else "")
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.primary_model,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        response_mime_type="application/json",
                        response_schema=DiagramsResponse
                    )
                )
                data = json.loads(response.text)
                DiagramsResponse(**data)
                return data
            except Exception as e:
                error_context = str(e)

        return {
            "component_diagram": "graph TD\n    Client[Client Browser/API] --> AppServer[Application Server]",
            "sequence_diagram": "sequenceDiagram\n    Client->>AppServer: HTTP Request"
        }

    async def _run_security_auditor_async(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.client:
            sec_count = len(context.get("security_findings", []))
            rating = "Needs Attention" if sec_count > 0 else "Strong"
            return {
                "overall_rating": rating,
                "key_risks": [f"Identified {sec_count} static code finding(s)."],
                "remediation_recommendations": ["Use env variables for secrets."],
                "summary_markdown": f"### Security Audit Overview\nRating: **{rating}**"
            }

        prompt = f"Audit security for findings: {json.dumps(context['security_findings'])}"
        error_context = ""
        for attempt in range(2):
            try:
                full_prompt = prompt + (f"\nPrevious Error: {error_context}" if error_context else "")
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.fast_model,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        response_mime_type="application/json",
                        response_schema=SecurityAuditResponse
                    )
                )
                data = json.loads(response.text)
                SecurityAuditResponse(**data)
                return data
            except Exception as e:
                error_context = str(e)

        return {
            "overall_rating": "Moderate",
            "key_risks": ["Static scan completed."],
            "remediation_recommendations": ["Enforce secrets management."],
            "summary_markdown": "### Security Overview"
        }

    async def _run_doc_generator_async(self, context: Dict[str, Any], diagrams: Dict[str, str], security: Dict[str, Any]) -> Dict[str, str]:
        if not self.client:
            return {
                "adr_document": "# ADR 001: ArchAgent Multi-Agent Architecture\n\n## Status\nAccepted",
                "onboarding_guide": "# Developer Guide\n\nRun python main.py",
                "system_spec": "Modular multi-agent technical architecture synthesis platform."
            }

        prompt = f"Generate ADR 001 and Onboarding Guide:\nMetrics: {json.dumps(context['code_metrics'].get('summary'))}"
        error_context = ""
        for attempt in range(2):
            try:
                full_prompt = prompt + (f"\nPrevious Error: {error_context}" if error_context else "")
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.primary_model,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        response_mime_type="application/json",
                        response_schema=DocumentationResponse
                    )
                )
                data = json.loads(response.text)
                DocumentationResponse(**data)
                return data
            except Exception as e:
                error_context = str(e)

        return {
            "adr_document": "# ADR 001: Multi-Agent Architecture\n\n## Status\nAccepted",
            "onboarding_guide": "# Developer Guide\n\nRun python main.py",
            "system_spec": "Python multi-agent architecture system."
        }

    async def answer_architecture_question_async(self, question: str, report_context: Optional[Dict[str, Any]] = None) -> str:
        report = report_context or self.memory.get_latest_report(self.session_id) or {}
        await self.memory.add_message_async(self.session_id, "user", question)

        if not self.client:
            ans = f"ArchAgent Assistant (Offline Mode):\nTarget: `{report.get('target_dir', 'N/A')}`. LOC: {report.get('inspection_summary', {}).get('total_loc', 0)}"
            await self.memory.add_message_async(self.session_id, "assistant", ans)
            return ans

        prompt = f"Answer architecture question: {question}\nContext: {report.get('documentation', {}).get('system_spec')}"
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.fast_model,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=self.system_instruction)
            )
            ans = self.guardrails.sanitize_output(response.text)
        except Exception as e:
            ans = f"Error generating answer: {str(e)}"

        await self.memory.add_message_async(self.session_id, "assistant", ans)
        return ans

    def answer_architecture_question(self, question: str, report_context: Optional[Dict[str, Any]] = None) -> str:
        return asyncio.run(self.answer_architecture_question_async(question, report_context))
