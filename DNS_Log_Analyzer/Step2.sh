for file in RAWLogs/*; do
  if [ -f "$file" ]; then
    sed -i '/^$/d' "$file"
  fi
done
