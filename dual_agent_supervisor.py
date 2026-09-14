#!/usr/bin/env python3
"""
dual_agent_supervisor.py - Dual-Agent Supervisor Workflow

Architecture:
1. Script Writer Agent: Generates or updates scripts based on specs & error logs.
2. Test Engineer Agent: Evaluates scripts against test suites & schema bounds.
3. Supervisor Orchestrator: Manages the context protocol and feedback retry loop.
"""

import sys
import os
import json
import subprocess
import argparse
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DualAgentSupervisor")


# =====================================================================
# 1. PROTOCOL MODELS
# =====================================================================

class TestResult(BaseModel):
    """Protocol payload representing test evaluation results."""
    status: str = "FAIL"  # "PASS" or "FAIL"
    exit_code: int = 1
    stdout: str = ""
    stderr: str = ""
    error_summary: str = ""


class SupervisorContext(BaseModel):
    """Protocol payload passed between Supervisor, Writer, and Tester agents."""
    task_id: str
    iteration: int = 1
    max_iterations: int = 5
    specification: str
    target_script: str
    test_script: str
    script_content: str = ""
    last_test_result: Optional[TestResult] = None

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)


# =====================================================================
# 2. SPECIALIST AGENTS
# =====================================================================

class ScriptWriterAgent:
    """Specialist agent responsible for generating and patching python scripts."""

    def __init__(self, name: str = "ScriptWriter"):
        self.name = name

    def generate_or_fix(self, context: SupervisorContext) -> str:
        """
        Generates or fixes script content based on current context and prior error logs.
        In live integration, this calls the LLM / Subagent prompt.
        """
        logger.info(f"[{self.name}] Processing specification for iteration {context.iteration}")
        
        if context.last_test_result and context.last_test_result.status == "FAIL":
            logger.warning(
                f"[{self.name}] Analyzing failure log from previous run:\n"
                f"--- Error Summary ---\n{context.last_test_result.error_summary}\n"
                f"--- Stderr Snippet ---\n{context.last_test_result.stderr[-300:] if context.last_test_result.stderr else 'N/A'}"
            )

        # Read existing script content if present
        if os.path.exists(context.target_script):
            with open(context.target_script, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info(f"[{self.name}] Read existing script content from {context.target_script}")
            return content
        else:
            logger.info(f"[{self.name}] Initializing new script template for {context.target_script}")
            return f"# Script generated for: {context.specification}\n"


class TestEngineerAgent:
    """Specialist agent responsible for validating scripts against test runners."""

    def __init__(self, name: str = "TestEngineer"):
        self.name = name

    def _get_python_bin(self) -> str:
        venv_python = os.path.join(os.path.dirname(__file__), ".venv", "bin", "python")
        if os.path.exists(venv_python):
            return venv_python
        return sys.executable

    def evaluate(self, context: SupervisorContext) -> TestResult:
        """
        Executes test_script using virtualenv python and inspects process outputs.
        """
        logger.info(f"[{self.name}] Running test suite '{context.test_script}' against '{context.target_script}'")

        if not os.path.exists(context.test_script):
            return TestResult(
                status="FAIL",
                exit_code=1,
                stderr=f"Test runner script not found: {context.test_script}",
                error_summary=f"Missing test runner file {context.test_script}"
            )

        python_bin = self._get_python_bin()
        cmd = [python_bin, context.test_script]

        logger.info(f"[{self.name}] Command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        stdout = result.stdout
        stderr = result.stderr
        exit_code = result.returncode

        if exit_code == 0:
            logger.info(f"[{self.name}] Execution passed with exit code 0.")
            return TestResult(
                status="PASS",
                exit_code=0,
                stdout=stdout,
                stderr=stderr,
                error_summary=""
            )
        else:
            logger.error(f"[{self.name}] Execution failed with exit code {exit_code}.")
            summary = "Test execution failed."
            if "Traceback" in stderr or "Traceback" in stdout:
                summary = "Python Traceback detected during test execution."
            elif "[FAIL]" in stdout:
                # Extract fail line
                for line in stdout.splitlines():
                    if "[FAIL]" in line:
                        summary = line.strip()
                        break

            return TestResult(
                status="FAIL",
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                error_summary=summary
            )


# =====================================================================
# 3. SUPERVISOR ORCHESTRATOR
# =====================================================================

class DualAgentSupervisor:
    """
    Orchestrates interaction between ScriptWriterAgent and TestEngineerAgent.
    Implements the iteration loop and protocol routing.
    """

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.writer = ScriptWriterAgent()
        self.tester = TestEngineerAgent()

    def run(self, task_id: str, specification: str, target_script: str, test_script: str) -> bool:
        """
        Executes the supervisor feedback loop until tests pass or max iterations reached.
        """
        logger.info(f"=== Starting Dual-Agent Supervisor Workflow: {task_id} ===")
        logger.info(f"Specification: {specification}")
        logger.info(f"Target Script: {target_script} | Test Script: {test_script}")

        context = SupervisorContext(
            task_id=task_id,
            iteration=1,
            max_iterations=self.max_iterations,
            specification=specification,
            target_script=target_script,
            test_script=test_script
        )

        while context.iteration <= context.max_iterations:
            logger.info(f"\n--- Iteration {context.iteration}/{context.max_iterations} ---")

            # Step 1: Script Writer generates / updates script
            script_code = self.writer.generate_or_fix(context)
            context.script_content = script_code

            # Step 2: Handoff to Test Engineer for evaluation
            test_result = self.tester.evaluate(context)
            context.last_test_result = test_result

            # Step 3: Evaluate result & Route
            if test_result.status == "PASS":
                logger.info(f"\n=========================================")
                logger.info(f" WORKFLOW PASSED AT ITERATION {context.iteration}")
                logger.info(f"=========================================\n")
                return True
            else:
                logger.warning(
                    f"Iteration {context.iteration} FAILED with exit code {test_result.exit_code}. "
                    f"Routing error logs back to Writer Agent..."
                )
                context.iteration += 1

        logger.error(f"\n=========================================")
        logger.error(f" WORKFLOW FAILED: Max iterations ({self.max_iterations}) reached.")
        logger.error(f"=========================================\n")
        return False


# =====================================================================
# CLI INTERFACE
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Dual-Agent Supervisor Workflow Runner")
    parser.add_argument("--task-id", type=str, default="task-001", help="Unique identifier for task")
    parser.add_argument("--spec", type=str, default="Validate metadata pipeline script", help="Feature specification")
    parser.add_argument("--script", type=str, default="fetch_catalog.py", help="Target script path")
    parser.add_argument("--test", type=str, default="test_pipeline.py", help="Test runner path")
    parser.add_argument("--max-iterations", type=int, default=3, help="Max retry loop iterations")
    parser.add_argument("--dry-run", action="store_true", help="Print protocol context without running loop")

    args = parser.parse_args()

    if args.dry_run:
        sample_context = SupervisorContext(
            task_id=args.task_id,
            specification=args.spec,
            target_script=args.script,
            test_script=args.test
        )
        print("=== Protocol Context Payload (Schema Validation Dry Run) ===")
        print(sample_context.to_json())
        return

    supervisor = DualAgentSupervisor(max_iterations=args.max_iterations)
    success = supervisor.run(
        task_id=args.task_id,
        specification=args.spec,
        target_script=args.script,
        test_script=args.test
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
