#!/bin/bash
cd "$(dirname "$0")"
if curl -fsS "http://127.0.0.1:13110/" >/dev/null 2>&1; then
  open "http://127.0.0.1:13110/"
  exit 0
fi
"./13110-server" &
SERVER_PID=$!
for _ in {1..40}; do
  if curl -fsS "http://127.0.0.1:13110/" >/dev/null 2>&1; then
    open "http://127.0.0.1:13110/"
    wait "$SERVER_PID"
    exit $?
  fi
  sleep 0.1
done
echo "13110 启动失败，请保留此窗口并联系制作方。"
read -r
