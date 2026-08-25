# XY Skill plugin marketplace demo
# Self-bootstrapped: cleans previous state, records a clean run against the real marketplace.

Output demo.gif
Set Theme "Catppuccin Latte"
Set FontSize 24
Set Width 1400
Set Height 600
Set Padding 20
Set TypingSpeed 10ms
Set Shell zsh

# Bootstrap (hidden): clean previous state, clear screen
Hide
Type "claude plugin uninstall xy@xy-skills 2>/dev/null; claude plugin marketplace remove xy-skills 2>/dev/null"
Enter
Sleep 4s
Type "clear"
Enter
Sleep 500ms
Show

# Add marketplace
Type "claude plugin marketplace add https://github.com/xyaz1313/xyskill.git"
Enter
Sleep 12s
Enter
Sleep 300ms

# Install
Type "claude plugin install xy@xy-skills"
Enter
Sleep 3s
Enter
Sleep 300ms

# Verify
Type "claude plugin list | grep -A2 xy"
Enter
Sleep 2s

Sleep 1s
