import os
import sys
import argparse

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("--topic", type=str, required=True, help="Research Topic for Comparison")
args = parser.parse_args()

# Hardcoded key as fallback
FALLBACK_KEY = "sk-c1a6b588f7d543adb0412c5bc61bdd7b"

# Ensure API Keys
if "QWEN_API_KEY" not in os.environ:
    compat_key = os.environ.get("OPENAI_COMPATIBILITY_API_KEY")
    if compat_key:
        os.environ["QWEN_API_KEY"] = compat_key
        print(f"Set QWEN_API_KEY from OPENAI_COMPATIBILITY_API_KEY")
    else:
        print(f"Warning: QWEN_API_KEY not found. Using fallback key.")
        os.environ["QWEN_API_KEY"] = FALLBACK_KEY

os.environ["OPENAI_API_KEY"] = os.environ["QWEN_API_KEY"]
# Set Base URL for CAMEL if needed (it might read from ENV)
os.environ["QWEN_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# Add path
sys.path.append("/root/autodl-tmp/Myexamples/comparative_experiments/Virtual-Scientists/sci_platform")

print(f"Launching Virtual Scientists with Qwen on Topic: '{args.topic}'...")
# Quote the topic to handle spaces
cmd = f"python /root/autodl-tmp/Myexamples/comparative_experiments/Virtual-Scientists/sci_platform/sci_platform_qwen.py --topic \"{args.topic}\""
os.system(cmd)
