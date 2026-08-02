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

Type "sudo -u gaidemo-copilot gaidemo-ticket-read 1 | jq '.ticket | {id, subject, status, updated_at}'"
Enter
Sleep 5s

Type "sudo -u gaidemo-copilot bash -lc 'cd ~/gaidemo && python3 -m democtl proposal preview artifacts/proposal.json'"
Enter
Sleep 7s

Type "sudo -u gaidemo-copilot bash -lc 'cd ~/gaidemo && python3 -m democtl proposal apply artifacts/proposal.json'"
Enter
Sleep 6s

Type "sudo gaidemo-proposal-apply APPROVE"
Enter
Sleep 7s

Type "exit"
Enter
Sleep 2s
