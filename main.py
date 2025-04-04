import time as tmr, argparse as ap, readchar as rc, platform as pf
from datetime import datetime as dt
from enum import Enum

class PState(Enum):
    GOOD = '\033[92m'
    WARN = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    def __add__(self, other):
        return str(self.value)+str(other)
    def __str__(self):
        return str(self.value)

class CState(Enum):
    INITIAL = 0
    ALPHANUM = 1
    BLANKPUNCT = 2


def main():
    """TypingStats main program"""

    if pf.system() == 'Linux':
        char_backspace = '\x7f'
        word_backspace = '\x08'
    else:
        char_backspace = '\x08'
        word_backspace = '\x7f'

    parser = ap.ArgumentParser(prog="TypingStats",
                               description="""Check your typing skills
                               against any text of your choice!""",
                               epilog='Developed by Jed Schaaf (2025)')
    parser.add_argument("--input", "-if",
                        help="Source file of text to use for typing test",
                        type=str, default="./test.txt")
    parser.add_argument("--output", "-of",
                        help="Statistics file to append typing results",
                        type=str, default="./results.txt")
    args = parser.parse_args()

    # get in/out files from cmd-line argument(s)
    in_file = args.input
    out_file = args.output

    # set up statistics counters
    all_chars_count = typed_keys_count = word_count = 0
    file_data = []
    correct_chars = []

    with open(in_file,'r') as f:
        for line in f: # read file into memory to avoid counting disk I/O time
            file_data.append(line.rstrip('\r\n'))

    start = tmr.perf_counter_ns() # start nanosecond timer
    first = True
    abort = False
    for line in file_data:
        content_state:CState = CState.INITIAL
        print(line)
        user_text = []
        next_ch, ctrl = readkbd() # wait for next keyboard input
        typed_keys_count += 1

        # reset start time in case user doesn't start typing immediately
        if first:
            first = False
            start = tmr.perf_counter_ns()

        while next_ch != rc.key.ENTER:

            if next_ch == char_backspace: # backtrack state
                if user_text:
                    next_ch = user_text.pop()
                    all_chars_count -= 1
                    correct_chars.pop()
                else:
                    next_ch = ''
                if next_ch != '':
                    if content_state == CState.ALPHANUM:
                        print(PState.ENDC+'\b \b', end='')
                        if str.isalnum(next_ch):
                            pass
                        elif str.isspace(next_ch) or not str.isprintable(next_ch):
                            content_state = CState.BLANKPUNCT
                            word_count -= 1
                    elif content_state == CState.BLANKPUNCT:
                        print(PState.ENDC+'\b \b', end='')
                        if str.isalnum(next_ch):
                            content_state = CState.ALPHANUM
                    elif content_state == CState.INITIAL:
                        pass
                if not user_text:
                    content_state = CState.INITIAL

            elif next_ch == word_backspace:
                if content_state == CState.ALPHANUM:
                    counter = 0
                    while user_text:
                        next_ch = user_text[-1]
                        if str.isalnum(next_ch):
                            user_text.pop()
                            all_chars_count -= 1
                            correct_chars.pop()
                            counter += 1
                        else:
                            content_state = CState.BLANKPUNCT
                            break
                    print(PState.ENDC+'\b'*counter+' '*counter+'\b'*counter, end='')
                    if not user_text:
                        content_state = CState.INITIAL
                    word_count -= 1
                elif content_state == CState.BLANKPUNCT:
                    counter = 0
                    while user_text:
                        next_ch = user_text[-1]
                        if str.isalnum(next_ch):
                            content_state = CState.ALPHANUM
                            break
                        else:
                            user_text.pop()
                            all_chars_count -= 1
                            correct_chars.pop()
                            counter += 1
                    print(PState.ENDC+'\b'*counter+' '*counter+'\b'*counter, end='')
                    if not user_text:
                        content_state = CState.INITIAL
                elif content_state == CState.INITIAL:
                    pass

            elif str.isprintable(next_ch):
                user_text.append(next_ch)
                y = line[len(user_text) - 1] if len(user_text) <= len(line) else ''

                # update word count
                if str.isalnum(next_ch):
                    if content_state != CState.ALPHANUM: # new word
                        word_count += 1
                    content_state = CState.ALPHANUM
                elif str.isspace(next_ch):
                    if content_state != CState.BLANKPUNCT: # new blank or punctuation
                        content_state = CState.BLANKPUNCT

                # update character counts
                if next_ch == '' and y != '':
                    print(PState.WARN+y, end='')
                    all_chars_count += 1
                    correct_chars.append(False)
                elif next_ch != '' and y == '':
                    print(PState.WARN+next_ch, end='')
                    all_chars_count += 1
                    correct_chars.append(False)
                elif next_ch != y: # show discrepancies
                    print(PState.FAIL+next_ch, end='')
                    all_chars_count += 1
                    correct_chars.append(False)
                elif next_ch == y:
                    print(PState.GOOD+next_ch, end='')
                    all_chars_count += 1
                    correct_chars.append(True)

            elif next_ch == rc.key.CTRL_C:
                abort = True # interrupt test and get current results
                break

            else:
                pass # ignore invalid input
                #print(repr(x)) #show me what was typed

            next_ch, ctrl = readkbd()
            typed_keys_count += 1

        if abort:
            print(PState.ENDC)
            break

        if len(user_text) < len(line):
            for m in range(len(user_text), len(line)):
                print(PState.WARN+line[m], end='')
                all_chars_count += 1

        print(PState.ENDC)
    duration = tmr.perf_counter_ns() - start # end nanosecond timer

    good = sum(correct_chars)
    results = calculate_results(duration, all_chars_count, typed_keys_count, good, word_count) # calculate results

    # display statistics
    print(f'duration: {duration/1_000_000_000:.1f} seconds')
    print(f'total characters: {all_chars_count}')
    print(f'correct characters: {good}')
    print(f'accuracy: {results[0]:.1%}')
    print(f'keys per second: {results[1]:.2f}')
    print(f'words per minute: {results[2]:.2f}')

    # save results for historical comparison
    with open(out_file, 'a') as fo:
        newline = '\n'
        fo.write(str(dt.now())+newline)
        fo.write(in_file+newline)
        fo.write(f'{duration}, {all_chars_count}, {good}, {word_count}')
        fo.write(newline+newline)

    # end of program


def readkbd():
    """read the next character or control character from the keyboard"""
    retval = rc.readchar()
    control = False
    if retval == '\000' or retval == '\xe0':
        control = True
        retval = rc.readchar()
    return retval, control


def calculate_results(duration, all_chars, typed_keys, good_chars, words):
    """determine keys-per-second, words-per-minute, accuracy, and other results"""
    accuracy = float(good_chars) / float(all_chars)
    kps = typed_keys / (duration / 1_000_000_000)
    wpm = words / (duration / 60_000_000_000)
    return accuracy, kps, wpm


if __name__ == '__main__':
    main()

