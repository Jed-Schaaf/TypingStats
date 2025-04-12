"""
Name: TypingStats
Description: A commandline/terminal application to measure
the user's typing speed and accuracy.
Author: Jed Schaaf
Date: 2025
"""
import argparse as ap
import locale as loc
import time as tmr
from datetime import datetime as dt
from enum import Enum
import readchar as rc


class PState(Enum):
    """Print State for character display"""
    GOOD = '\033[92m'
    WARN = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    def __add__(self, other):
        return str(self.value)+str(other)
    def __str__(self):
        return str(self.value)


class CState(Enum):
    """Character State to facilitate counting words"""
    INITIAL = 0
    ALPHANUM = 1
    BLANKPUNCT = 2


def main():
    """TypingStats main program"""

    # *nix systems and Windows swap backspace and ctrl+backspace codes
    if rc.key.BACKSPACE == '\x08':
        word_backspace = '\x7f'
    else:
        word_backspace = '\x08'

    parser = setup_parser()
    args = parser.parse_args()

    # set up statistics counters
    stat_counters = {"all_chars": 0, "typed_keys": 0, "words": 0}
    file_data = []
    correct_chars = []

    local_encoding = loc.getpreferredencoding()

    def remove_last_char():
        """internal function to remove (and return) the last typed character"""
        stat_counters["all_chars"] -= 1
        if correct_chars:
            correct_chars.pop()
        if user_text:
            retval = user_text.pop()
        else:
            retval = ''
        return retval

    def erase_char(n: int = 1):
        """internal function to clear the last n typed characters from the screen"""
        print(PState.ENDC + '\b'*n + ' '*n + '\b'*n, end='')

    def remove_char(next_char):
        """internal function to remove a character from current typing line"""
        nonlocal content_state
        if content_state == CState.INITIAL:
            return
        erase_char()
        if content_state == CState.ALPHANUM and not str.isalnum(next_char):
            content_state = CState.BLANKPUNCT
            stat_counters["words"] -= 1
        elif content_state == CState.BLANKPUNCT and str.isalnum(next_char):
            content_state = CState.ALPHANUM

    def remove_char_set(next_char):
        """internal function to remove a set of similar characters from current typing line"""
        nonlocal content_state
        if content_state == CState.INITIAL:
            return
        char_set_counter = 0
        while user_text:
            next_char = user_text[-1]
            if content_state == CState.ALPHANUM and not str.isalnum(next_char):
                content_state = CState.BLANKPUNCT
                stat_counters["words"] -= 1
                break
            if content_state == CState.BLANKPUNCT and str.isalnum(next_char):
                content_state = CState.ALPHANUM
                break
            remove_last_char()
            char_set_counter += 1
        erase_char(char_set_counter)
        if not user_text:
            content_state = CState.INITIAL


    try:
        with open(args.input, 'rt', encoding=local_encoding) as f:
            for line in f: # read file into memory to avoid counting disk I/O time
                file_data.append(line.rstrip('\r\n'))
    except IOError as err:
        print('Could not find, open, or read test file')
        print(err)
        parser.print_help()
        return 1

    start = tmr.perf_counter_ns() # start nanosecond timer
    first = True
    abort = False
    for line in file_data:
        content_state:CState = CState.INITIAL
        print(line)
        user_text = []
        next_ch, ctrl = readkbd() # wait for next keyboard input
        stat_counters["typed_keys"] += 1

        # reset start time in case user doesn't start typing immediately
        if first:
            first = False
            start = tmr.perf_counter_ns()

        while next_ch != rc.key.ENTER:

            # backtrack state for one character
            if next_ch == rc.key.BACKSPACE:
                if user_text:
                    next_ch = remove_last_char()
                else:
                    next_ch = ''
                if next_ch != '':
                    remove_char(next_ch)
                if not user_text:
                    content_state = CState.INITIAL

            # backtrack state for contiguous similar characters
            elif next_ch == word_backspace:
                remove_char_set(next_ch)

            # display next typed character
            elif str.isprintable(next_ch) and not ctrl:
                user_text.append(next_ch)
                test_base = line[len(user_text) - 1] if len(user_text) <= len(line) else ''

                # update word count
                if str.isalnum(next_ch):
                    if content_state != CState.ALPHANUM: # new word
                        stat_counters["words"] += 1
                    content_state = CState.ALPHANUM
                elif str.isspace(next_ch):
                    if content_state != CState.BLANKPUNCT: # new blank or punctuation
                        content_state = CState.BLANKPUNCT

                # update character counts
                stat_counters["all_chars"] += 1
                if next_ch == '' and test_base != '': # missed characters in active typing
                    print(PState.WARN+test_base, end='') # not sure how this could happen
                    correct_chars.append(False)
                elif next_ch != '' and test_base == '': # show extra characters
                    print(PState.WARN+next_ch, end='')
                    correct_chars.append(False)
                elif next_ch != test_base: # show discrepancies
                    print(PState.FAIL+next_ch, end='')
                    correct_chars.append(False)
                elif next_ch == test_base: # show correct characters
                    print(PState.GOOD+next_ch, end='')
                    correct_chars.append(True)

            # interrupt test and get current results
            elif next_ch in (rc.key.ESC, rc.key.CTRL_C,
                             rc.key.CTRL_Q, rc.key.CTRL_Z):
                abort = True
                break

            # ignore invalid input
            else:
                pass

            next_ch, ctrl = readkbd()
            stat_counters["typed_keys"] += 1

        if abort:
            print(PState.ENDC)
            break

        # show missed characters
        if len(user_text) < len(line):
            for m in range(len(user_text), len(line)):
                print(PState.WARN+line[m], end='')
                stat_counters["all_chars"] += 1

        print(PState.ENDC)
    duration = tmr.perf_counter_ns() - start # end nanosecond timer

    good_chars_count = sum(correct_chars)
    results = calculate_results(duration, stat_counters, good_chars_count)

    # display statistics
    display_results(duration, stat_counters["all_chars"], good_chars_count, results)

    # save results for historical comparison
    save_results(args.output, args.input, duration,
                 stat_counters, good_chars_count)

    return 0 # end of main()


def setup_parser():
    """configure help and command-line parameters"""
    parser = ap.ArgumentParser(prog="TypingStats",
                               description="""Check your typing skills
                                   against any text of your choice!""",
                               epilog='Developed by Jed Schaaf (2025)')
    parser.add_argument("--input", "-if",
                        help="Source file of text to use for typing test",
                        type=str, default="./test.txt")
    # test.txt = The quick brown fox jumps over the lazy dog.
    # test0.txt = Lorem Ipsum
    # test1.txt = Psalm 23
    # test2.txt = Ozymandias
    parser.add_argument("--output", "-of",
                        help="Statistics file to append typing results",
                        type=str, default="./results.txt")
    return parser


def readkbd():
    """read the next character or control character from the keyboard"""
    retval = rc.readchar()
    control = False
    if retval in ('\000', '\xe0'):
        control = True
        retval = rc.readchar()
    return retval, control


def calculate_results(duration, stats, good_chars):
    """determine keys-per-second, words-per-minute, accuracy, and other results"""
    accuracy = float(good_chars) / float(stats["all_chars"])
    kps = stats["typed_keys"] / (duration / 1_000_000_000)
    wpm = stats["words"] / (duration / 60_000_000_000)
    return accuracy, kps, wpm


def display_results(duration, all_chars_count, good_chars_count, results):
    """show results on stdout"""
    print(f'duration: {duration / 1_000_000_000:.1f} seconds')
    print(f'total characters: {all_chars_count}')
    print(f'correct characters: {good_chars_count}')
    print(f'accuracy: {results[0]:.1%}')
    print(f'keys per second: {results[1]:.2f}')
    print(f'words per minute: {results[2]:.2f}')


def save_results(out_file, in_file, duration, stats, good_chars_count):
    """add results to selected file"""
    try:
        local_encoding = loc.getpreferredencoding()
        with open(out_file, 'at', encoding=local_encoding) as fo:
            newline = rc.key.ENTER
            fo.write(str(dt.now())+newline)
            fo.write(in_file+newline)
            fo.write(f'dur:{duration}, len:{stats["all_chars"]}, '+
                     f'good:{good_chars_count}, words:{stats["words"]}')
            fo.write(newline+newline)
    except IOError as err:
        print('Could not save results')
        print(err)


if __name__ == '__main__':
    main()
