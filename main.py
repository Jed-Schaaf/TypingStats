"""
Name: TypingStats
Description: A commandline/terminal application to measure
the user's typing speed and accuracy.
Author: Jed Schaaf
Date: 2025
"""
import argparse as ap
import glob
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
    DEFAULT = '\033[0m'
    def __add__(self, other):
        return str(self.value)+str(other)
    def __str__(self):
        return str(self.value)


class CState(Enum):
    """Character State to facilitate counting words"""
    INITIAL = 0
    ALPHANUM = 1
    BLANK_OR_PUNCTUATION = 2

class Console:
    """input and output controls"""

    def clear_screen(self):
        """clear and reset the terminal screen"""
        print("\033c" # reset terminal
              "\033[3J" # clear scroll-back history
              "\033[2J" # clear current screen
              "\033[0m" # default styling
              "\033[H", # set cursor to the top-left corner
              end='') # do not print newline


    def erase_char(self, n: int = 1):
        """clear the last n typed characters from the screen"""
        print(PState.DEFAULT + '\b' * n + ' ' * n + '\b' * n, end='')


    def main_menu(self):
        """display welcome and menu"""
        self.clear_screen()
        print("TypingStats")
        # print list of test files
        root = "./tests/"
        test_files = glob.glob("test*.txt", root_dir=root)
        test_files.sort()
        i = 0
        for i, test_file in enumerate(test_files):
            try:
                with open(root + test_file, "rt",
                          encoding=loc.getpreferredencoding()) as tf:
                    print(str(i) + ". " + tf.readline().strip()[:50] + "...")
            except IOError:
                print(str(i) + ". " + test_file + " (caution: may not work)")
        response = input("Select a test # to run or enter 'Q' to quit: ").strip()
        while True:
            if response.isdigit():
                if 0 <= int(response) < len(test_files):
                    return root + test_files[int(response)]
            elif response.upper() == 'Q':
                return 'Q'
            print("Invalid response.")
            response = input("Select a test # to run or enter 'Q' to quit: ").strip()


    def setup_parser(self):
        """configure help and command-line parameters"""
        parser = ap.ArgumentParser(prog="TypingStats",
                                   description="""Check your typing skills
                                       against any text of your choice!""",
                                   epilog="Developed by Jed Schaaf (2025)")
        parser.add_argument("--input", "-if",
                            help="Source file of text to use for typing test",
                            type=str)
        parser.add_argument("--output", "-of",
                            help="Statistics file to append typing results",
                            type=str, default="./results.txt")
        return parser


    def read_kbd(self):
        """read the next character or control character from the keyboard"""
        retval = rc.readchar()
        control = False
        if retval in ('\000', '\xe0'):
            control = True
            retval = rc.readchar()
        return retval, control


class Main:
    """TypingStats main class"""

    word_backspace:str
    stat_counters:dict
    file_data:list
    correct_chars:list
    user_text:list
    content_state:CState
    parser:ap.ArgumentParser
    args:ap.Namespace
    console:Console

    def __init__(self):
        """TypingStats default setup"""
        # Windows and *nix systems swap backspace and ctrl+backspace codes
        if rc.key.BACKSPACE == '\x08':
            self.word_backspace = '\x7f'
        else:
            self.word_backspace = '\x08'
        self.console = Console()
        self.parser = self.console.setup_parser()


    def reset_stats(self):
        """Reset statistic counters"""
        self.stat_counters = {"all_chars": 0, "typed_keys": 0, "words": 0}
        self.file_data = []
        self.correct_chars = []

    def main(self):
        """TypingStats main program"""

        self.args = self.parser.parse_args()

        in_file = self.args.input if self.args.input else self.console.main_menu()
        while in_file != 'Q':

            # set up statistics counters
            self.reset_stats()

            try:
                with open(in_file, 'rt',
                          encoding=loc.getpreferredencoding()) as f:
                    for line in f: # read file into memory to avoid counting disk I/O time
                        self.file_data.append(line.rstrip('\r\n'))
            except IOError as err:
                print("Could not find, open, or read test file")
                print(err)
                self.parser.print_help()
                return 1

            first = True
            abort = False
            self.console.clear_screen()
            print("Begin typing whenever you are ready:")
            start = 0 #
            for line in self.file_data:
                self.content_state = CState.INITIAL
                print(line)
                self.user_text = []
                next_ch, ctrl = self.console.read_kbd() # wait for next keyboard input
                self.stat_counters["typed_keys"] += 1

                # start nanosecond timer once user begins typing
                if first:
                    first = False
                    start = tmr.perf_counter_ns()

                while next_ch != rc.key.ENTER:

                    # backtrack state for one character
                    if next_ch == rc.key.BACKSPACE:
                        self.remove_char(next_ch)

                    # backtrack state for contiguous similar characters
                    elif next_ch == self.word_backspace:
                        self.remove_char_set(next_ch)

                    # display next typed character
                    elif str.isprintable(next_ch) and not ctrl:
                        self.user_text.append(next_ch)
                        if len(self.user_text) <= len(line):
                            test_base = line[len(self.user_text) - 1]
                        else:
                            test_base = ''

                        # update word count
                        if str.isalnum(next_ch):
                            if self.content_state != CState.ALPHANUM: # new word
                                self.stat_counters["words"] += 1
                            self.content_state = CState.ALPHANUM
                        elif str.isspace(next_ch):
                            # new blank or punctuation
                            if self.content_state != CState.BLANK_OR_PUNCTUATION:
                                self.content_state = CState.BLANK_OR_PUNCTUATION

                        # update character counts
                        self.stat_counters["all_chars"] += 1
                        if next_ch == '' and test_base != '': # missed characters in active typing
                            print(PState.WARN+test_base, end='') # not sure how this could happen
                            self.correct_chars.append(False)
                        elif next_ch != '' and test_base == '': # show extra characters
                            print(PState.WARN+next_ch, end='')
                            self.correct_chars.append(False)
                        elif next_ch != test_base: # show discrepancies
                            print(PState.FAIL+next_ch, end='')
                            self.correct_chars.append(False)
                        elif next_ch == test_base: # show correct characters
                            print(PState.GOOD+next_ch, end='')
                            self.correct_chars.append(True)

                    # interrupt test and get current results
                    elif next_ch in (rc.key.ESC, rc.key.CTRL_C,
                                     rc.key.CTRL_Q, rc.key.CTRL_Z):
                        abort = True
                        break

                    # ignore invalid input
                    else:
                        pass

                    next_ch, ctrl = self.console.read_kbd()
                    self.stat_counters["typed_keys"] += 1

                if abort:
                    print(PState.DEFAULT)
                    break

                # show missed characters
                if len(self.user_text) < len(line):
                    for m in range(len(self.user_text), len(line)):
                        print(PState.WARN+line[m], end='')
                        self.stat_counters["all_chars"] += 1

                print(PState.DEFAULT)
            duration = tmr.perf_counter_ns() - start # end nanosecond timer

            good_chars_count = sum(self.correct_chars)
            results = self.calculate_results(duration, good_chars_count)

            # display statistics
            self.display_results(duration, good_chars_count, results)

            # save results for historical comparison
            self.save_results(in_file, duration, good_chars_count)

            print("Press any key to continue...")
            self.console.read_kbd()
            in_file = self.console.main_menu()

        print("Your results are saved in <" + self.args.output + ">.\n" +
              "Hope you enjoyed testing your typing skills!")
        return 0 # end of main()


    def remove_last_char(self):
        """remove (and return) the last typed character"""
        self.stat_counters["all_chars"] -= 1
        if self.correct_chars:
            self.correct_chars.pop()
        if self.user_text:
            retval = self.user_text.pop()
        else:
            retval = ''
        return retval


    def remove_char(self, next_char):
        """remove a character from current typing line"""
        if self.content_state == CState.INITIAL:
            return
        self.console.erase_char()
        next_char = self.remove_last_char()
        if self.content_state == CState.ALPHANUM and not str.isalnum(next_char):
            self.content_state = CState.BLANK_OR_PUNCTUATION
            self.stat_counters["words"] -= 1
        elif self.content_state == CState.BLANK_OR_PUNCTUATION and str.isalnum(next_char):
            self.content_state = CState.ALPHANUM


    def remove_char_set(self, next_char):
        """remove a set of similar characters from current typing line"""
        if self.content_state == CState.INITIAL:
            return
        char_set_counter = 0
        while self.user_text:
            next_char = self.user_text[-1]
            if self.content_state == CState.ALPHANUM and not str.isalnum(next_char):
                self.content_state = CState.BLANK_OR_PUNCTUATION
                self.stat_counters["words"] -= 1
                break
            if self.content_state == CState.BLANK_OR_PUNCTUATION and str.isalnum(next_char):
                self.content_state = CState.ALPHANUM
                break
            self.remove_last_char()
            char_set_counter += 1
        self.console.erase_char(char_set_counter)
        if not self.user_text:
            self.content_state = CState.INITIAL


    def calculate_results(self, duration, good_chars):
        """determine keys-per-second, words-per-minute, accuracy, and other results"""
        if float(self.stat_counters["all_chars"]) != 0.0:
            accuracy = float(good_chars) / float(self.stat_counters["all_chars"])
        else:
            accuracy = 0.0
        kps = self.stat_counters["typed_keys"] / (duration / 1_000_000_000)
        wpm = self.stat_counters["words"] / (duration / 60_000_000_000)
        return accuracy, kps, wpm


    def display_results(self, duration, good_chars_count, results):
        """show results on stdout"""
        print(f'duration: {duration / 1_000_000_000:.1f} seconds')
        print(f'total characters: {self.stat_counters["all_chars"]}')
        print(f'correct characters: {good_chars_count}')
        print(f'accuracy: {results[0]:.1%}')
        print(f'keys per second: {results[1]:.2f}')
        print(f'words per minute: {results[2]:.2f}')


    def save_results(self, in_file, duration, good_chars_count):
        """add results to selected file"""
        try:
            local_encoding = loc.getpreferredencoding()
            with open(self.args.output, 'at', encoding=local_encoding) as fo:
                newline = rc.key.ENTER
                fo.write(str(dt.now())+newline)
                fo.write(in_file+newline)
                fo.write(f'dur:{duration}, len:{self.stat_counters["all_chars"]}, '+
                         f'good:{good_chars_count}, words:{self.stat_counters["words"]}')
                fo.write(newline+newline)
        except IOError as err:
            print("Could not save results")
            print(err)


# --------sentinel-------- #
if __name__ == '__main__':
    Main().main()
