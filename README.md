# TypingStats

This is a simple command-line program developed in 2025 by Jed Schaaf as a capstone project for NCLab's Python training course.
It uses the readchar library from PyPI: https://pypi.org/project/readchar/

The program compares keyboard-typed user input against a user-supplied test file and calculates several typing statistics, including typing accuracy as a percentage of correctly typed keys and speed as measured via keys-per-second (kps) and words-per-minute (wpm). The test file can be any input that Python can open as a file and read as text. User input comes from stdin (usually the keyboard).

The text from the test file will be displayed line-by-line, with user input interspersed after each line. Correct, incorrect, extra, and missed characters are displayed as the user types them in.

If the user makes a mistake, the current line can be corrected using backspace to delete the last character or ctrl+backspace to delete the last set of alphanumeric characters or the last set of whitespace and punctuation. The corrected text will count in favor of accuracy, but will also affect the kps and wpm measurements.

If the user does not wish to finish the entire test file, ctrl+c may be pressed to interrupt the testing and calculate the results up to that point.
