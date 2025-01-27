#!/bin/bash

# Get the current date
CURRENT_DAY=$(date +%d)
CURRENT_DAY_OF_WEEK=$(date +%u)

# Check if today is the third Monday of the month
if [ "$CURRENT_DAY_OF_WEEK" -eq 1 ] && [ "$CURRENT_DAY" -ge 15 ] && [ "$CURRENT_DAY" -le 21 ]; then
  # Run apt-get update commands
  echo "Running apt-get update..."
  sudo apt-get update
  sudo apt-get update

  # Check if a reboot is needed
  if [ -f /var/run/reboot-required ]; then
    echo "Reboot is required. Rebooting now..."
    sudo reboot
  else
    echo "No reboot is required."
  fi
else
  echo "Today is not the third Monday of the month. Script will not run."
fi
