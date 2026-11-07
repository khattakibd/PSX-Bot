import subprocess
import sys

def run_script(script_name):
    print(f"\n{'='*40}")
    print(f"🚀 Running {script_name}...")
    print(f"{'='*40}")
    try:
        # Runs the script and waits for it to finish
        subprocess.run([sys.executable, script_name], check=True)
    except subprocess.CalledProcessError:
        print(f"❌ Error occurred in {script_name}. Stopping.")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ {script_name} not found in this folder.")
        sys.exit(1)

if __name__ == "__main__":
    # Run all three steps in order
    run_script("step1.py")
    run_script("step2.py")
    run_script("step3.py")
    
    print("\n✅ ALL DONE! Open index.html to view your dashboard.")