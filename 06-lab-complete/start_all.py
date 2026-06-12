"""Python Process Supervisor to start and manage the multi-agent system."""
from __future__ import annotations

import sys
import os
import time
import signal
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger("supervisor")

# List of modules to start
MODULES = [
    "registry",
    "tax_agent",
    "compliance_agent",
    "law_agent",
    "customer_agent",
]

processes: list[subprocess.Popen] = []
shutting_down = False

def terminate_all(sig, frame):
    global shutting_down
    if shutting_down:
        return
    shutting_down = True
    logger.info("Termination signal received. Shutting down all agents gracefully...")
    for p in processes:
        if p.poll() is None:
            logger.info("Terminating process PID %d...", p.pid)
            p.terminate()
            
    # Wait for all processes to exit
    for p in processes:
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning("Process PID %d did not exit. Killing it...", p.pid)
            p.kill()
    logger.info("All processes stopped.")
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, terminate_all)
signal.signal(signal.SIGTERM, terminate_all)

def main():
    logger.info("Starting Legal Multi-Agent System...")
    
    # Start modules one by one with a slight delay
    for module in MODULES:
        logger.info("Starting module: python -m %s", module)
        python_exe = sys.executable
        # On Windows, sys.executable inside uv can sometimes point to the base system interpreter
        # instead of the virtualenv python. Fallback to "python" to look it up in PATH.
        if "venv" not in python_exe.lower() and ".venv" not in python_exe.lower():
            python_exe = "python"

        # Propagate virtualenv site-packages and app directories to PYTHONPATH for subprocesses
        env = os.environ.copy()
        python_path_entries = [p for p in sys.path if "site-packages" in p or "dist-packages" in p or ".venv" in p or p == os.getcwd()]
        if python_path_entries:
            sep = ";" if os.name == "nt" else ":"
            existing_pp = env.get("PYTHONPATH", "")
            if existing_pp:
                env["PYTHONPATH"] = sep.join(python_path_entries) + sep + existing_pp
            else:
                env["PYTHONPATH"] = sep.join(python_path_entries)

        p = subprocess.Popen(
            [python_exe, "-m", module],
            stdout=sys.stdout,
            stderr=sys.stderr,
            env=env
        )
        processes.append(p)
        # Give registry/agents some time to start up and bind to ports
        time.sleep(3.0 if module in ("registry", "compliance_agent") else 1.5)

    logger.info("All modules started. Monitoring processes...")
    
    # Monitoring loop
    while not shutting_down:
        for p in processes:
            exit_code = p.poll()
            if exit_code is not None:
                logger.error("Process PID %d exited unexpectedly with code %d", p.pid, exit_code)
                # If any critical service dies, terminate everything and exit
                terminate_all(None, None)
        time.sleep(1.0)

if __name__ == "__main__":
    main()
