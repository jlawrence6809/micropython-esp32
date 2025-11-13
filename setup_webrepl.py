# setup_webrepl.py - Helper script to configure WebREPL
# Upload this and run it once to set up WebREPL

import webrepl_setup

# This will prompt you to:
# 1. Enable WebREPL on boot (yes/no)
# 2. Set a password (remember this!)
# 3. Reboot when done

print("Running WebREPL setup...")
print("Follow the prompts to enable WebREPL")
webrepl_setup.main()

