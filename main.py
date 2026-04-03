import subprocess

processes = []

try:
    # Start pygame traffic simulation
    processes.append(subprocess.Popen(["python", "simulation.py"]))

    # Start vehicle detector
    processes.append(subprocess.Popen(["python", "detector.py"]))

    # Start Flask backend
    processes.append(subprocess.Popen(["python", "service.py"]))

    # Start Streamlit dashboard
    processes.append(subprocess.Popen(["streamlit", "run", "dashboard.py"]))

    # Wait until user stops with CTRL+C
    print("All services are running... Press CTRL+C to stop.")
    for p in processes:
        p.wait()

except KeyboardInterrupt:
    print("Stopping all processes...")
    for p in processes:
        p.terminate()
