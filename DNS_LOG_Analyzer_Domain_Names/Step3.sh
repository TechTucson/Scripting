for file in RAWLogs/*; do
  if [ -f "$file" ]; then
    awk '{print $NF}' "$file" >> Output.txt
  fi
done
