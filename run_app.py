"""
Minimal App Launcher - Executes the split app parts in sequence
"""

# Execute Part 1: Imports and Utils
exec(open('app_part1_imports_and_utils.py', encoding='utf-8').read())

# Execute Part 2: Main UI (includes the main() function definition)
exec(open('app_part2_main_ui.py', encoding='utf-8').read())

# Call main() only once
main()
