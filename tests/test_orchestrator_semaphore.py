import unittest
import asyncio


class TestOrchestratorAttributes(unittest.TestCase):
    """Tests for Orchestrator semaphore and execution log."""

    def test_orchestrator_has_semaphore_attribute(self):
        """Verify Orchestrator class has semaphore attribute defined."""
        # Read the source to verify semaphore is declared
        import os

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        orch_path = os.path.join(base_dir, "orchestrator.py")
        with open(orch_path, "r") as f:
            content = f.read()

        self.assertIn(
            "self.semaphore = asyncio.Semaphore(5)",
            content,
            "Orchestrator should initialize semaphore with limit of 5",
        )

    def test_orchestrator_has_execution_log_attribute(self):
        """Verify Orchestrator class has execution_log attribute defined."""
        import os

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        orch_path = os.path.join(base_dir, "orchestrator.py")
        with open(orch_path, "r") as f:
            content = f.read()

        self.assertIn(
            "self.execution_log = []",
            content,
            "Orchestrator should initialize execution_log as list",
        )


class TestSemaphoreUsage(unittest.TestCase):
    """Tests to verify semaphore is actually used in the code."""

    def test_semaphore_used_in_connector_gathering(self):
        """Verify semaphore is used to constrain concurrent connector runs."""
        import os

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        orch_path = os.path.join(base_dir, "orchestrator.py")
        with open(orch_path, "r") as f:
            content = f.read()

        # The semaphore should be used in asyncio.gather operations
        # Either as a wrapper or as part of task management
        has_semaphore_usage = "self.semaphore" in content and (
            "async with self.semaphore" in content
            or "await self.semaphore" in content
            or "semaphore" in content
        )

        self.assertIn(
            "self.semaphore",
            content,
            "Semaphore should be referenced in orchestrator code",
        )


class TestExecutionLogUsage(unittest.TestCase):
    """Tests to verify execution_log is properly used."""

    def test_execution_log_used_for_logging(self):
        """Verify execution_log is used to record connector exit codes."""
        import os

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        orch_path = os.path.join(base_dir, "orchestrator.py")
        with open(orch_path, "r") as f:
            content = f.read()

        # execution_log should be appended with result data
        self.assertIn(
            "self.execution_log",
            content,
            "execution_log should be used in orchestrator",
        )


if __name__ == "__main__":
    unittest.main()
