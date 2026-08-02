Output artifacts/terminal.mp4

Set Shell "bash"
Set FontSize 20
Set Width 1440
Set Height 900
Set Padding 28
Set MarginFill "#111827"
Set WindowBar Colorful
Set TypingSpeed 28ms
Set PlaybackSpeed 1
Env PATH "recording/bin:/home/jahwag/.local/bin:/usr/local/bin:/usr/bin:/bin"

Type "ssh gaidemo"
Enter
Sleep 2s
Type "sudo clem status"
Enter
Sleep 4s
Type "systemctl is-active gaidemo-agentbus gaidemo-live-cockpit gaidemo-freshservice-approval gaidemo-agentbus-approval"
Enter
Sleep 4s
Type "sudo -u gaidemo-copilot gaidemo-ticket-read 2 | jq '.ticket | {id, subject, status, updated_at}'"
Enter
Sleep 5s
Type "sudo -u gaidemo-copilot bash -lc 'cd ~/gaidemo && python3 -m democtl proposal preview artifacts/proposal.json'"
Enter
Sleep 7s
Type "curl -s -o /dev/null -w 'cockpit approval endpoint: HTTP %{http_code}\\n' -X POST http://127.0.0.1:8765/api/approve"
Enter
Sleep 4s
Type "sudo -u gaidemo-approver test ! -r /etc/gaidemo/freshworks.env && echo 'approval watcher has no write credential'"
Enter
Sleep 4s
Type "exit"
Enter
Sleep 2s
